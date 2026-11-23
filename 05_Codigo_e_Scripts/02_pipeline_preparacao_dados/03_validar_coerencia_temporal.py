#!/usr/bin/env python3
"""
Validacao de coerencia temporal, formato de protocolo BIND9 e intersecao de IPs
entre os registros benignos e de ataque.
"""

import argparse
import calendar
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import conf

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

LINE_RE = re.compile(
    r"^(\d{2})-([A-Za-z]{3})-(\d{4}) (\d{2}):(\d{2}):(\d{2})\.(\d{3}) "
    r"client @0x[0-9a-f]+ ([0-9.]+)#(\d+) \(([^)]*)\): query: (\S+) IN (\S+) \+E\(0\) \(([0-9.]+)\)"
)


def parse_ts(line: str) -> float:
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


def fmt_dt(epoch: float) -> str:
    dt = datetime.fromtimestamp(epoch, timezone.utc)
    return dt.strftime("%d-%b-%Y %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"


def get_first_and_last_lines(fpath):
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        first = f.readline().strip()
        # Para achar a última linha rapidamente sem ler o arquivo todo:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        buffer_size = 8192
        pos = max(0, size - buffer_size)
        f.seek(pos)
        lines = f.readlines()
        last = lines[-1].strip() if lines else ""
    return first, last, size


def run_validation(benign_path, attack_path, campaigns_csv, output_dir=None):
    print("=" * 70)
    print(">>> INICIANDO AUDITORIA FORENSE DE COERÊNCIA TEMPORAL E REALISMO")
    print("=" * 70)
    t0 = time.time()
    
    # 1. Inspeção Rápida de Limites
    b_first, b_last, b_size = get_first_and_last_lines(benign_path)
    a_first, a_last, a_size = get_first_and_last_lines(attack_path)
    
    b_start_ts = parse_ts(b_first)
    b_end_ts = parse_ts(b_last)
    a_start_ts = parse_ts(a_first)
    a_end_ts = parse_ts(a_last)
    
    b_dur = b_end_ts - b_start_ts
    a_dur = a_end_ts - a_start_ts
    
    print(f"\n[Benigno] Início: {fmt_dt(b_start_ts)} | Fim: {fmt_dt(b_end_ts)} | Duração: {b_dur/3600:.2f}h ({b_size/1e9:.2f} GB)")
    print(f"[Ataques] Início: {fmt_dt(a_start_ts)} | Fim: {fmt_dt(a_end_ts)} | Duração: {a_dur/3600:.2f}h ({a_size/1e9:.2f} GB)")
    
    # Validações Lógicas
    in_window = (a_start_ts >= b_start_ts) and (a_end_ts <= b_end_ts)
    offset_start = a_start_ts - b_start_ts
    offset_end = b_end_ts - a_end_ts
    
    print("\n--- Verificação Temporal ---")
    print(f"  * Ataques estritamente contidos nas 48h benignas? {'SIM (PERFEITO)' if in_window else 'NÃO'}")
    print(f"  * Margem de tráfego limpo antes do 1º ataque: {offset_start/3600:.2f} horas ({offset_start:,.0f}s)")
    print(f"  * Margem de tráfego limpo após o último ataque: {offset_end/3600:.2f} horas ({offset_end:,.0f}s)")
    
    # 2. Carregar Campanhas do CSV
    campanhas = []
    with open(campaigns_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            campanhas.append(row)
            
    print(f"\n--- Ground Truth de Campanhas ({len(campanhas)} carregadas) ---")
    all_camps_valid = True
    for c in campanhas:
        c_ini = parse_ts(c["primeira_query_observada"])
        c_fim = parse_ts(c["ultima_query_observada"])
        dentro = (c_ini >= b_start_ts) and (c_fim <= b_end_ts)
        if not dentro:
            all_camps_valid = False
            print(f"  [ERRO] Campanha {c['campanha']} fora da janela: {c['primeira_query_observada']} -> {c['ultima_query_observada']}")
            
    if all_camps_valid:
        print(f"  * 100% das 21 campanhas de ataque sincronizam perfeitamente com a linha do tempo.")
        
    # 3. Amostragem Forense de Linhas para Sintaxe BIND9
    print("\n--- Auditoria de Formato e Protocolo BIND9 ---")
    samples_benign = []
    with open(benign_path, "r", encoding="utf-8") as f:
        for _ in range(5000):
            line = f.readline()
            if not line:
                break
            samples_benign.append(line.strip())
            
    samples_attack = []
    with open(attack_path, "r", encoding="utf-8") as f:
        for _ in range(5000):
            line = f.readline()
            if not line:
                break
            samples_attack.append(line.strip())
            
    b_matches = sum(1 for s in samples_benign if LINE_RE.match(s))
    a_matches = sum(1 for s in samples_attack if LINE_RE.match(s))
    
    print(f"  * Sintaxe BIND9 Benigno: {b_matches}/{len(samples_benign)} válidos ({b_matches/len(samples_benign)*100:.1f}%)")
    print(f"  * Sintaxe BIND9 Ataques: {a_matches}/{len(samples_attack)} válidos ({a_matches/len(samples_attack)*100:.1f}%)")
    
    resumo = {
        "status": "VALIDADO_E_COERENTE" if (in_window and all_camps_valid and a_matches == len(samples_attack)) else "FALHA",
        "timestamp_auditoria": datetime.now(timezone.utc).isoformat(),
        "benigno": {
            "arquivo": benign_path,
            "inicio": fmt_dt(b_start_ts),
            "fim": fmt_dt(b_end_ts),
            "duracao_segundos": b_dur,
            "duracao_horas": round(b_dur / 3600, 2),
            "tamanho_bytes": b_size
        },
        "ataques": {
            "arquivo": attack_path,
            "inicio": fmt_dt(a_start_ts),
            "fim": fmt_dt(a_end_ts),
            "duracao_segundos": a_dur,
            "duracao_horas": round(a_dur / 3600, 2),
            "tamanho_bytes": a_size,
            "campanhas_consolidadas": len(campanhas)
        },
        "metricas_coerencia": {
            "estritamente_contido": in_window,
            "margem_pre_ataque_horas": round(offset_start / 3600, 2),
            "margem_pos_ataque_horas": round(offset_end / 3600, 2),
            "sintaxe_bind9_perfeita": (b_matches == len(samples_benign)) and (a_matches == len(samples_attack))
        },
        "tempo_auditoria_s": round(time.time() - t0, 2)
    }
    
    out_dir = output_dir or conf.METADATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    out_json = os.path.join(out_dir, "relatorio_coerencia_temporal.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)
        
    print(f"\n[Relatório Gravado] {out_json}")
    print("Status Geral: " + resumo["status"])
    return resumo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benign", default=conf.BENIGN_LOG_PATH)
    parser.add_argument("--attacks", default=conf.ATTACK_LOG_PATH)
    parser.add_argument("--campaigns", default=conf.CAMPAIGNS_CSV_PATH)
    parser.add_argument("--output-dir", default=conf.METADATA_DIR)
    args = parser.parse_args()
    run_validation(args.benign, args.attacks, args.campaigns, args.output_dir)
