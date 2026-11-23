#!/usr/bin/env python3
"""
Normalizacao deterministica dos enderecos IP de origem nos logs de ataque BIND9.
Redistribui as consultas a partir do pool de clientes simulados (10.0.0.0/16)
para eliminar vies de classificacao por sub-rede (shortcut learning).
"""

import argparse
import calendar
import csv
import glob
import hashlib
import ipaddress
import json
import os
import random
import re
import sys
import time
from bisect import bisect_right
from datetime import datetime, timedelta, timezone

# --------------------------------------------------------------------------
# Parametros cientificos (espelham dns-log-generator/config/config.py)
# --------------------------------------------------------------------------
SEED = 129547711
INTERNAL_NETWORK = "10.0.0.0/16"
TOTAL_USERS = 25000
PROFILE_DISTRIBUTION = [
    ("student_user", 25),
    ("office_employee", 25),
    ("home_user", 25),
    ("devops_engineer", 5),
    ("casual_mobile_user", 20),
]

LAB_ATTACKER_IP = "192.168.2.201"
RESOLVER_IP = "192.168.0.10"      # identico a Dns(resolver_ip=...) do gerador
QUERY_FLAGS = "+E(0)"             # identico ao log benigno
EPHEMERAL_MIN, EPHEMERAL_MAX = 49152, 65535  # User._generate_ephemeral_port

# Distribuicao de enderecos IP de origem (IPs internos da sub-rede, IPs externos) por nivel
POOL_SIZES = {"LEVE": (15, 10), "MODERADO": (60, 40), "INTENSO": (250, 150)}
DEFAULT_DURATION = {"LEVE": 600, "MODERADO": 900, "INTENSO": 1800}
MARGIN_SECONDS = 120  # tolerancia ao redor da janela agendada do dnsperf

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

LINE_RE = re.compile(
    r"(\d{2})-([A-Za-z]{3})-(\d{4}) (\d{2}):(\d{2}):(\d{2})\.(\d{3}) "
    r"client @\w+ ([0-9.]+)#(\d+) \(([^)]*)\): query: (\S+) IN (\S+) (\S+) \(([0-9.]+)\)"
)


def sha256_text(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def sha256_file(path: str, chunk: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Pool de usuarios internos (reproduz UserManager do gerador benigno)
# --------------------------------------------------------------------------
def reproduce_user_pool(seed=SEED, network=INTERNAL_NETWORK, total=TOTAL_USERS):
    rng = random.Random(seed)
    hosts = list(ipaddress.ip_network(network).hosts())
    used, users = set(), []
    for profile, pct in PROFILE_DISTRIBUTION:
        for _ in range(int(total * (pct / 100))):
            while True:
                ip = str(rng.choice(hosts))
                if ip not in used:
                    used.add(ip)
                    break
            users.append((ip, profile))
    return users


def client_ptr(ip: str, port: int) -> str:
    """Identico a core/log_formatter.py::Dns._client_ptr."""
    return "0x" + hashlib.sha256(f"{ip}:{port}".encode()).hexdigest()[:12]


# --------------------------------------------------------------------------
# Campanhas (ground truth do dnsperf)
# --------------------------------------------------------------------------
def load_campaigns(campaign_dir):
    files = sorted(glob.glob(os.path.join(campaign_dir, "ataque_nxdomain_*.txt")))
    campaigns = []
    for fpath in files:
        fname = os.path.basename(fpath)
        m = re.match(r"ataque_nxdomain_(\d{8})_(\d{4})_(\w+)\.txt", fname)
        if not m:
            continue
        date_s, time_s, level = m.groups()
        start = duration = qps = None
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        ms = re.search(r"Started at:\s+(.+)", content)
        if ms:
            try:
                start = datetime.strptime(re.sub(r"\s+", " ", ms.group(1).strip()),
                                          "%a %b %d %H:%M:%S %Y")
            except ValueError:
                pass
        ml = re.search(r"-l\s+(\d+)", content)
        mq = re.search(r"-Q\s+(\d+)", content)
        duration = int(ml.group(1)) if ml else None
        qps = int(mq.group(1)) if mq else None
        source = "dnsperf" if start else "nome_do_arquivo"
        if start is None:
            start = datetime.strptime(f"{date_s} {time_s}", "%Y%m%d %H%M")
        if duration is None:
            duration = DEFAULT_DURATION[level]
        campaigns.append({
            "id": len(campaigns) + 1, "file": fname, "level": level,
            "start": start, "end": start + timedelta(seconds=duration),
            "duration": duration, "qps_cfg": qps, "start_source": source,
        })
    campaigns.sort(key=lambda c: c["start"])
    for i, c in enumerate(campaigns, 1):
        c["id"] = i
    return campaigns


def naive_epoch(dt: datetime) -> float:
    return float(calendar.timegm(dt.timetuple()))


# --------------------------------------------------------------------------
# Distribuicao de enderecos IP de origem por campanha para integracao nos logs
# --------------------------------------------------------------------------
def random_global_ips(rng, n, exclude):
    out = []
    while len(out) < n:
        ip = ipaddress.ip_address(rng.getrandbits(32))
        s = str(ip)
        if (ip.is_global and not ip.is_multicast and not ip.is_reserved
                and s not in exclude and s not in out):
            out.append(s)
    return out


def build_campaign_ips(campaign, users, seed=SEED):
    rng = random.Random(int(sha256_text(f"{seed}-attack-{campaign['id']}-{campaign['level']}")[:16], 16))
    n_int, n_ext = POOL_SIZES[campaign["level"]]
    internal = rng.sample(users, n_int)  # [(ip, perfil)]
    internal_ips = {ip for ip, _ in internal}
    external = random_global_ips(rng, n_ext, internal_ips)
    ips_pool = [(ip, f"interno:{prof}") for ip, prof in internal] + [(ip, "externo") for ip in external]
    rng.shuffle(ips_pool)
    return ips_pool


def fmt_ts(epoch: float) -> str:
    dt = datetime.fromtimestamp(epoch, timezone.utc)
    return dt.strftime("%d-%b-%Y %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"


# --------------------------------------------------------------------------
def run(args):
    t0 = time.time()
    users = reproduce_user_pool()
    user_ips = {ip for ip, _ in users}
    print(f"[pool] {len(users)} usuarios internos reconstruidos (SEED={SEED}, {INTERNAL_NETWORK})")

    verify = None
    if args.benign_ips_file:
        with open(args.benign_ips_file) as f:
            benign = {l.strip() for l in f if l.strip()}
        verify = {
            "benign_unique_ips": len(benign),
            "pool_unique_ips": len(user_ips),
            "identicos": benign == user_ips,
            "benign_fora_do_pool": len(benign - user_ips),
            "pool_ausente_no_benigno": len(user_ips - benign),
        }
        print(f"[verificacao pool vs log benigno] {verify}")
        if not verify["identicos"]:
            print("[ALERTA] pool reconstruido difere do observado no log benigno")

    campaigns = load_campaigns(args.campaign_dir)
    print(f"[campanhas] {len(campaigns)} carregadas")
    for c in campaigns:
        c["ips_origem"] = build_campaign_ips(c, users)
        c["s_ts"] = naive_epoch(c["start"]) - args.margin
        c["e_ts"] = naive_epoch(c["end"]) + args.margin
        c.update(queries=0, first=None, last=None)
        print(f"  C{c['id']:02d} {c['level']:8s} {c['start']} -> {c['end']} "
              f"({c['duration']}s, inicio via {c['start_source']}) ips_dist={len(c['ips_origem'])}")
    for a, b in zip(campaigns, campaigns[1:]):
        assert a["e_ts"] < b["s_ts"], "janelas de campanha sobrepostas; reduza --margin"
    starts = [c["s_ts"] for c in campaigns]

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "ataques_unificados.log")
    day_cache, ptr_cache, port_cache = {}, {}, {}
    ip_counts = {}
    out_sha = hashlib.sha256()
    total = lab = written = unparsed = other_ip = outside = 0
    outside_by_day, unparsed_samples = {}, []

    with open(args.input, "r", encoding="utf-8", errors="ignore") as fin, \
            open(out_path, "wb") as fout:
        buf = []
        for raw in fin:
            total += 1
            if args.limit_lines and total > args.limit_lines:
                break
            if LAB_ATTACKER_IP not in raw:
                continue
            lab += 1
            m = LINE_RE.search(raw)
            if not m:
                unparsed += 1
                if len(unparsed_samples) < 5:
                    unparsed_samples.append(raw.strip()[:200])
                continue
            dd, mon, yyyy, hh, mi, ss, ms, cip, port, dom_p, dom_q, qtype, _flags, _srv = m.groups()
            if cip != LAB_ATTACKER_IP:
                other_ip += 1
                continue
            key = (dd, mon, yyyy)
            base = day_cache.get(key)
            if base is None:
                base = day_cache[key] = float(calendar.timegm((int(yyyy), MONTHS[mon], int(dd), 0, 0, 0)))
            ts = base + int(hh) * 3600 + int(mi) * 60 + int(ss) + int(ms) / 1000.0
            idx = bisect_right(starts, ts) - 1
            if idx < 0 or ts > campaigns[idx]["e_ts"]:
                outside += 1
                d = f"{dd}-{mon}-{yyyy}"
                outside_by_day[d] = outside_by_day.get(d, 0) + 1
                continue
            c = campaigns[idx]
            h = int(hashlib.sha256(f"{SEED}:{c['id']}:{port}:{dom_q}".encode()).hexdigest()[:8], 16)
            src_ip, _origin = c["ips_origem"][h % len(c["ips_origem"])]
            pk = (c["id"], src_ip, port)
            new_port = port_cache.get(pk)
            if new_port is None:
                hp = int(sha256_text(f"{SEED}:{c['id']}:{src_ip}:{port}")[:8], 16)
                new_port = port_cache[pk] = EPHEMERAL_MIN + hp % (EPHEMERAL_MAX - EPHEMERAL_MIN + 1)
            ptr = ptr_cache.get((src_ip, new_port))
            if ptr is None:
                ptr = ptr_cache[(src_ip, new_port)] = client_ptr(src_ip, new_port)
            buf.append(f"{dd}-{mon}-{yyyy} {hh}:{mi}:{ss}.{ms} client @{ptr} {src_ip}#{new_port} "
                       f"({dom_p}): query: {dom_q} IN {qtype} {QUERY_FLAGS} ({RESOLVER_IP})\n")
            written += 1
            c["queries"] += 1
            if c["first"] is None:
                c["first"] = ts
            c["last"] = ts
            bk = (c["id"], src_ip)
            ip_counts[bk] = ip_counts.get(bk, 0) + 1
            if len(buf) >= 100000:
                blob = "".join(buf).encode()
                out_sha.update(blob)
                fout.write(blob)
                buf.clear()
            if written % 2_000_000 == 0:
                el = time.time() - t0
                print(f"[progresso] {written:,} consultas remapeadas | {total:,} linhas lidas | {el:,.0f}s", flush=True)
        if buf:
            blob = "".join(buf).encode()
            out_sha.update(blob)
            fout.write(blob)

    # ---------------- CSVs ----------------
    with open(os.path.join(args.output_dir, "ataques_campanhas.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["campanha", "nivel", "arquivo_dnsperf", "inicio_agendado", "fim_agendado", "origem_inicio",
                    "primeira_query_observada", "ultima_query_observada", "duracao_observada_s",
                    "queries", "qps_medio_observado", "qps_cfg_dnsperf", "ips_internos", "ips_externos"])
        for c in campaigns:
            obs = (c["last"] - c["first"]) if c["first"] is not None else 0
            n_int = sum(1 for _, o in c["ips_origem"] if o.startswith("interno"))
            w.writerow([c["id"], c["level"], c["file"], c["start"], c["end"], c["start_source"],
                        fmt_ts(c["first"]) if c["first"] else "", fmt_ts(c["last"]) if c["last"] else "",
                        f"{obs:.1f}", c["queries"], f"{c['queries'] / obs:.1f}" if obs else "0",
                        c["qps_cfg"] or "", n_int, len(c["ips_origem"]) - n_int])
    with open(os.path.join(args.output_dir, "ataques_ips_distribuicao.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["campanha", "ip", "origem", "queries"])
        for c in campaigns:
            for ip, origin in c["ips_origem"]:
                w.writerow([c["id"], ip, origin, ip_counts.get((c["id"], ip), 0)])

    all_ips = [ip for c in campaigns for ip, _ in c["ips_origem"]]
    manifest = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "seed": SEED, "rede_interna": INTERNAL_NETWORK, "total_usuarios_pool": TOTAL_USERS,
        "ip_lab_atacante_original": LAB_ATTACKER_IP, "resolver_normalizado": RESOLVER_IP,
        "flags_normalizadas": QUERY_FLAGS, "faixa_portas": [EPHEMERAL_MIN, EPHEMERAL_MAX],
        "distribuicao_ips_por_nivel": POOL_SIZES, "margem_janela_s": args.margin,
        "linhas_lidas": total, "linhas_com_ip_lab": lab, "consultas_remapeadas": written,
        "linhas_nao_parseadas": unparsed, "amostras_nao_parseadas": unparsed_samples,
        "linhas_ip_lab_fora_das_janelas": outside, "fora_das_janelas_por_dia": outside_by_day,
        "ips_unicos_atacantes": len(set(all_ips)),
        "ips_atacantes_internos_unicos": len({ip for c in campaigns for ip, o in c["ips_origem"] if o.startswith("interno")}),
        "verificacao_pool_vs_log_benigno": verify,
        "sha256_script": sha256_file(os.path.abspath(__file__)),
        "sha256_saida": out_sha.hexdigest(),
        "sha256_entrada": sha256_file(args.input) if args.hash_input else None,
        "tamanho_entrada_bytes": os.path.getsize(args.input),
        "tamanho_saida_bytes": os.path.getsize(out_path),
        "tempo_execucao_s": round(time.time() - t0, 1),
    }
    with open(os.path.join(args.output_dir, "ataques_manifesto.json"), "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n=== RESUMO ===")
    print(f"linhas lidas: {total:,} | com IP do lab: {lab:,} | remapeadas: {written:,} | "
          f"fora das janelas: {outside:,} | nao parseadas: {unparsed:,}")
    for c in campaigns:
        print(f"  C{c['id']:02d} {c['level']:8s} queries={c['queries']:>12,} "
              f"obs={fmt_ts(c['first']) if c['first'] else '-'} -> {fmt_ts(c['last']) if c['last'] else '-'}")
    print(f"saida: {out_path} ({manifest['tamanho_saida_bytes'] / 1e9:.2f} GB) sha256={manifest['sha256_saida'][:16]}...")


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    flood = os.path.join(base, "06_Datasets_e_Logs", "nxdomain_flood")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=os.path.join(flood, "nxdomain.log"))
    ap.add_argument("--campaign-dir", default=flood)
    ap.add_argument("--output-dir", default=os.path.join(base, "06_Datasets_e_Logs", "logs"))
    ap.add_argument("--margin", type=int, default=MARGIN_SECONDS)
    ap.add_argument("--limit-lines", type=int, default=0, help="somente para testes")
    ap.add_argument("--benign-ips-file", default=None,
                    help="arquivo com IPs de origem unicos do log benigno para verificar o pool")
    ap.add_argument("--hash-input", action="store_true", help="calcula SHA-256 do log bruto (lento)")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
