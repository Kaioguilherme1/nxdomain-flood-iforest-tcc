#!/usr/bin/env python3
"""
Particionamento e consolidacao dos logs DNS benignos e de ataque em blocos de 24h e 48h.
"""

import argparse
import calendar
import csv
import glob
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def sha256_file(path: str, chunk: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def processar_benigno(benign_src, out_dir):
    print("\n" + "=" * 60)
    print(">>> 1. PROCESSANDO TRÁFEGO BENIGNO (SEPARAÇÃO POR DIA)")
    print("=" * 60)
    t0 = time.time()
    
    dir_benigno = os.path.join(out_dir, "benigno_separado")
    os.makedirs(dir_benigno, exist_ok=True)
    
    path_dia1 = os.path.join(dir_benigno, "benigno_dia1_2026-06-07.log")
    path_dia2 = os.path.join(dir_benigno, "benigno_dia2_2026-06-08.log")
    
    count_dia1 = 0
    count_dia2 = 0
    count_outros = 0
    total = 0
    
    buf_d1 = []
    buf_d2 = []
    
    with open(benign_src, "r", encoding="utf-8", errors="ignore") as fin, \
         open(path_dia1, "w", encoding="utf-8") as f1, \
         open(path_dia2, "w", encoding="utf-8") as f2:
        
        for line in fin:
            total += 1
            if line.startswith("07-Jun-2026"):
                buf_d1.append(line)
                count_dia1 += 1
            elif line.startswith("08-Jun-2026"):
                buf_d2.append(line)
                count_dia2 += 1
            else:
                count_outros += 1
            
            if len(buf_d1) >= 100000:
                f1.writelines(buf_d1)
                buf_d1.clear()
            if len(buf_d2) >= 100000:
                f2.writelines(buf_d2)
                buf_d2.clear()
                
            if total % 10_000_000 == 0:
                el = time.time() - t0
                print(f"[benigno] {total:,} linhas lidas ({el:.0f}s) | Dia 1: {count_dia1:,} | Dia 2: {count_dia2:,}", flush=True)
                
        if buf_d1:
            f1.writelines(buf_d1)
        if buf_d2:
            f2.writelines(buf_d2)

    # Link simbólico ou referência para o benigno unificado
    unificado_dst = os.path.join(out_dir, "benigno_unificado.log")
    if not os.path.exists(unificado_dst):
        try:
            os.symlink(os.path.abspath(benign_src), unificado_dst)
            print(f"[link] Criado symlink {unificado_dst} -> {benign_src}")
        except Exception as e:
            print(f"[aviso] Não foi possível criar symlink: {e}")

    el = time.time() - t0
    res = {
        "arquivo_origem": benign_src,
        "total_consultas_benignas": total,
        "dia1_2026_06_07": {
            "arquivo": path_dia1,
            "consultas": count_dia1,
            "tamanho_bytes": os.path.getsize(path_dia1),
        },
        "dia2_2026_06_08": {
            "arquivo": path_dia2,
            "consultas": count_dia2,
            "tamanho_bytes": os.path.getsize(path_dia2),
        },
        "outras_linhas": count_outros,
        "tempo_s": round(el, 2)
    }
    print(f"\n[Concluído Benigno] Total: {total:,} | Dia 1: {count_dia1:,} ({res['dia1_2026_06_07']['tamanho_bytes']/1e9:.2f} GB) | "
          f"Dia 2: {count_dia2:,} ({res['dia2_2026_06_08']['tamanho_bytes']/1e9:.2f} GB) em {el:.1f}s")
    return res


def carregar_campanhas(campanhas_csv):
    campanhas = []
    with open(campanhas_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = int(row["campanha"])
            nivel = row["nivel"]
            # Ex: 07-Jun-2026 20:00:22.302
            obs_ini = row["primeira_query_observada"]
            obs_fim = row["ultima_query_observada"]
            campanhas.append({
                "id": cid,
                "nivel": nivel,
                "arquivo_dnsperf": row["arquivo_dnsperf"],
                "obs_ini": obs_ini,
                "obs_fim": obs_fim,
                "queries_esperadas": int(row["queries"]),
                "n_int": int(row.get("ips_internos", 0)),
                "n_ext": int(row.get("ips_externos", 0))
            })
    return campanhas


def parse_timestamp(line: str) -> float:
    # 07-Jun-2026 20:00:22.302
    try:
        dd = int(line[0:2])
        mon = MONTHS[line[3:6]]
        yyyy = int(line[7:11])
        hh = int(line[12:14])
        mi = int(line[15:17])
        ss = int(line[18:20])
        ms = int(line[21:24])
        base = calendar.timegm((yyyy, mon, dd, 0, 0, 0))
        return base + hh * 3600 + mi * 60 + ss + ms / 1000.0
    except Exception:
        return 0.0


def processar_ataques(attack_src, campanhas_csv, out_dir):
    print("\n" + "=" * 60)
    print(">>> 2. PROCESSANDO TRÁFEGO DE ATAQUES (SEPARAÇÃO POR CAMPANHA E ORIGEM)")
    print("=" * 60)
    t0 = time.time()
    
    dir_campanhas = os.path.join(out_dir, "ataques_separados")
    os.makedirs(dir_campanhas, exist_ok=True)
    
    campanhas = carregar_campanhas(campanhas_csv)
    print(f"[campanhas] {len(campanhas)} campanhas carregadas do CSV")
    
    # Criar arquivos para cada campanha
    camp_handles = {}
    camp_buffers = {}
    camp_counts = {}
    camp_paths = {}
    
    for c in campanhas:
        cid = c["id"]
        fname = f"ataque_C{cid:02d}_{c['nivel']}.log"
        fpath = os.path.join(dir_campanhas, fname)
        camp_paths[cid] = fpath
        camp_handles[cid] = open(fpath, "w", encoding="utf-8")
        camp_buffers[cid] = []
        camp_counts[cid] = 0
        
    path_int = os.path.join(dir_campanhas, "ataques_origem_interna.log")
    path_ext = os.path.join(dir_campanhas, "ataques_origem_externa.log")
    f_int = open(path_int, "w", encoding="utf-8")
    f_ext = open(path_ext, "w", encoding="utf-8")
    buf_int = []
    buf_ext = []
    count_int = 0
    count_ext = 0
    
    total = 0
    
    # Regex para capturar IP de origem
    ip_re = re.compile(r"client @0x[0-9a-f]+ ([0-9.]+)#")
    
    # Range timestamp por campanha (com margem de 60s)
    # Como as campanhas no arquivo consolidado estão ordenadas no tempo:
    camp_ranges = []
    for c in campanhas:
        t_ini = parse_timestamp(c["obs_ini"]) - 2.0
        t_fim = parse_timestamp(c["obs_fim"]) + 2.0
        camp_ranges.append((c["id"], t_ini, t_fim))
        
    cur_idx = 0
    n_ranges = len(camp_ranges)
    
    with open(attack_src, "r", encoding="utf-8", errors="ignore") as fin:
        for line in fin:
            total += 1
            ts = parse_timestamp(line)
            
            # Localizar campanha
            matched_cid = None
            if cur_idx < n_ranges:
                cid, s, e = camp_ranges[cur_idx]
                if ts < s:
                    # Antes da janela atual, pode ser da anterior se houver jitter
                    if cur_idx > 0 and ts <= camp_ranges[cur_idx-1][2]:
                        matched_cid = camp_ranges[cur_idx-1][0]
                elif ts <= e:
                    matched_cid = cid
                else:
                    # Passou da janela atual, avança
                    while cur_idx < n_ranges and ts > camp_ranges[cur_idx][2]:
                        cur_idx += 1
                    if cur_idx < n_ranges and ts >= camp_ranges[cur_idx][1]:
                        matched_cid = camp_ranges[cur_idx][0]
            
            if matched_cid:
                camp_buffers[matched_cid].append(line)
                camp_counts[matched_cid] += 1
                if len(camp_buffers[matched_cid]) >= 50000:
                    camp_handles[matched_cid].writelines(camp_buffers[matched_cid])
                    camp_buffers[matched_cid].clear()
                    
            # Separar interno vs externo
            m = ip_re.search(line)
            if m:
                src_ip = m.group(1)
                if src_ip.startswith("10.0."):
                    buf_int.append(line)
                    count_int += 1
                else:
                    buf_ext.append(line)
                    count_ext += 1
            else:
                # Fallback caso formato varie
                buf_ext.append(line)
                count_ext += 1
                
            if len(buf_int) >= 50000:
                f_int.writelines(buf_int)
                buf_int.clear()
            if len(buf_ext) >= 50000:
                f_ext.writelines(buf_ext)
                buf_ext.clear()
                
            if total % 5_000_000 == 0:
                el = time.time() - t0
                print(f"[ataques] {total:,} linhas separadas ({el:.0f}s) | Internos: {count_int:,} | Externos: {count_ext:,}", flush=True)

    # Flush final
    for cid in camp_handles:
        if camp_buffers[cid]:
            camp_handles[cid].writelines(camp_buffers[cid])
        camp_handles[cid].close()
        
    if buf_int:
        f_int.writelines(buf_int)
    f_int.close()
    if buf_ext:
        f_ext.writelines(buf_ext)
    f_ext.close()
    
    el = time.time() - t0
    res = {
        "arquivo_origem": attack_src,
        "total_consultas_ataque": total,
        "origem_interna_ips": {
            "arquivo": path_int,
            "consultas": count_int,
            "tamanho_bytes": os.path.getsize(path_int)
        },
        "origem_externa_ips": {
            "arquivo": path_ext,
            "consultas": count_ext,
            "tamanho_bytes": os.path.getsize(path_ext)
        },
        "campanhas_individuais": {
            cid: {
                "arquivo": camp_paths[cid],
                "consultas": camp_counts[cid],
                "tamanho_bytes": os.path.getsize(camp_paths[cid])
            }
            for cid in camp_paths
        },
        "tempo_s": round(el, 2)
    }
    print(f"\n[Concluído Ataques] Total: {total:,} | Internos: {count_int:,} ({res['origem_interna_ips']['tamanho_bytes']/1e9:.2f} GB) | "
          f"Externos: {count_ext:,} ({res['origem_externa_ips']['tamanho_bytes']/1e9:.2f} GB) em {el:.1f}s")
    return res


def main():
    parser = argparse.ArgumentParser(description="Particionamento de logs benignos e de ataque")
    parser.add_argument("--benign-src", default=None)
    parser.add_argument("--attack-src", default=None)
    parser.add_argument("--campanhas-csv", default=None)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()
    
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = args.out_dir or os.path.join(base, "06_Datasets_e_Logs", "logs")
    os.makedirs(out_dir, exist_ok=True)
    
    benign_src = args.benign_src
    attack_src = args.attack_src or os.path.join(out_dir, "ataques_unificados.log")
    campanhas_csv = args.campanhas_csv or os.path.join(out_dir, "ataques_campanhas.csv")
    
    t0_global = time.time()
    manifesto = {
        "data_execucao": datetime.now(timezone.utc).isoformat(),
        "hardware": "AMD Ryzen 5 7600 (6 cores / 12 threads), 16 GB DDR5, NVMe",
    }
    
    if benign_src and os.path.exists(benign_src):
        manifesto["benigno"] = processar_benigno(benign_src, out_dir)
    else:
        print(f"[pular] Arquivo benigno não informado ou não encontrado: {benign_src}")
        
    if attack_src and os.path.exists(attack_src):
        manifesto["ataques"] = processar_ataques(attack_src, campanhas_csv, out_dir)
    else:
        print(f"[pular] Arquivo de ataques não encontrado: {attack_src}")
        
    manifesto["tempo_total_s"] = round(time.time() - t0_global, 2)
    
    manifest_path = os.path.join(out_dir, "separacao_manifesto.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifesto, f, indent=2, ensure_ascii=False)
        
    print(f"\n[Manifesto Gravado] {manifest_path}")
    print("Processamento de separação concluído com sucesso!")


if __name__ == "__main__":
    main()
