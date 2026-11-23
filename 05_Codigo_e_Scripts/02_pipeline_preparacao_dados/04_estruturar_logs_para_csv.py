#!/usr/bin/env python3
"""
Conversao em streaming dos logs textuais do BIND9 para formato tabular CSV compactado.
"""

import argparse
import calendar
import csv
import gzip
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import conf

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

CSV_HEADER = [
    "datetime", "timestamp_epoch", "client_ip", "client_port",
    "client_ptr", "domain", "qtype", "flags", "resolver_ip", "label"
]


def parse_line_fast(raw_line: str, label: int):
    """
    Parser ultrarrápido otimizado para a sintaxe padrão do BIND9:
    Ex: 07-Jun-2026 20:00:22.302 client @0x5b3f7a1c890d 10.0.12.34#52145 (dom.com): query: dom.com IN A +E(0) (192.168.0.10)
    """
    p = raw_line.split()
    if len(p) >= 12 and p[2] == "client" and p[6] == "query:":
        date_str = p[0]
        time_str = p[1]
        
        # Parse timestamp epoch
        try:
            dd = int(date_str[0:2])
            mon = MONTHS[date_str[3:6]]
            yyyy = int(date_str[7:11])
            hh = int(time_str[0:2])
            mi = int(time_str[3:5])
            ss = int(time_str[6:8])
            ms = int(time_str[9:12])
            base_epoch = calendar.timegm((yyyy, mon, dd, 0, 0, 0))
            ts_epoch = base_epoch + hh * 3600 + mi * 60 + ss + ms / 1000.0
        except Exception:
            ts_epoch = 0.0

        ip_port = p[4].split("#")
        client_ip = ip_port[0]
        client_port = ip_port[1] if len(ip_port) > 1 else "53"
        client_ptr = p[3][1:] if p[3].startswith("@") else p[3]
        domain = p[7]
        qtype = p[9]
        flags = p[10]
        resolver_ip = p[11].strip("()")

        return [
            f"{date_str} {time_str}",
            f"{ts_epoch:.3f}",
            client_ip,
            client_port,
            client_ptr,
            domain,
            qtype,
            flags,
            resolver_ip,
            str(label)
        ]
    return None


def line_generator(fpath, label, limit=0):
    """Gera tuplas (timestamp_epoch, row_list) lendo o arquivo em streaming."""
    count = 0
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            row = parse_line_fast(line, label)
            if row:
                count += 1
                yield (float(row[1]), row)
                if limit and count >= limit:
                    break


def run_pipeline(args):
    print("=" * 75)
    print(">>> PIPELINE DE ESTRUTURAÇÃO TABULAR DE LOGS DNS (BIND9 -> CSV)")
    print("=" * 75)
    t0_global = time.time()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    path_sample = os.path.join(args.output_dir, "dns_eventos_estruturados_amostra.csv")
    path_full_gz = os.path.join(args.output_dir, "dns_eventos_estruturados_48h.csv.gz")
    path_full_raw = os.path.join(args.output_dir, "dns_eventos_estruturados_48h.csv")
    
    print(f"[*] Origem Benigno: {args.benign}")
    print(f"[*] Origem Ataques: {args.attacks}")
    print(f"[*] Diretório de Saída: {args.output_dir}")
    print(f"[*] Amostra descompactada: {args.sample_size:,} linhas -> {path_sample}")
    
    # 1. Gerar Amostra Rápida para Inspeção Imediata do Usuário
    print("\n[Etapa 1/2] Gerando amostra representativa intercalada...")
    sample_rows = []
    
    # Pegar 50k linhas benignas e 50k linhas de ataque
    half_sample = args.sample_size // 2
    b_sample_count = 0
    with open(args.benign, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            r = parse_line_fast(line, 0)
            if r:
                sample_rows.append(r)
                b_sample_count += 1
                if b_sample_count >= half_sample:
                    break
                    
    a_sample_count = 0
    with open(args.attacks, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            r = parse_line_fast(line, 1)
            if r:
                sample_rows.append(r)
                a_sample_count += 1
                if a_sample_count >= half_sample:
                    break
                    
    # Ordenar amostra por timestamp
    sample_rows.sort(key=lambda r: float(r[1]))
    
    with open(path_sample, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(CSV_HEADER)
        writer.writerows(sample_rows)
        
    print(f"[OK] Amostra gravada com sucesso: {len(sample_rows):,} linhas ({os.path.getsize(path_sample)/1e6:.2f} MB)")
    print(f"     * Linhas normais (label=0): {b_sample_count:,}")
    print(f"     * Linhas maliciosas (label=1): {a_sample_count:,}")

    # 2. Processamento Completo em Streaming Cronológico (Merge 2-Way)
    print("\n[Etapa 2/2] Processando unificação cronológica completa com flags (label 0/1)...")
    
    use_gzip = not args.no_compress
    target_path = path_full_gz if use_gzip else path_full_raw
    print(f"[*] Destino consolidado: {target_path} (Compactação Gzip: {use_gzip})")
    
    total_written = 0
    total_benign = 0
    total_attacks = 0
    
    gen_b = line_generator(args.benign, 0, limit=args.limit_benign)
    gen_a = line_generator(args.attacks, 1, limit=args.limit_attacks)
    
    # Abrir arquivo de destino
    out_file = gzip.open(target_path, "wt", encoding="utf-8") if use_gzip else open(target_path, "w", newline="", encoding="utf-8")
    writer = csv.writer(out_file)
    writer.writerow(CSV_HEADER)
    
    buf = []
    t_start_merge = time.time()
    
    item_b = next(gen_b, None)
    item_a = next(gen_a, None)
    
    while item_b is not None or item_a is not None:
        if item_b is not None and item_a is not None:
            if item_b[0] <= item_a[0]:
                buf.append(item_b[1])
                total_benign += 1
                item_b = next(gen_b, None)
            else:
                buf.append(item_a[1])
                total_attacks += 1
                item_a = next(gen_a, None)
        elif item_b is not None:
            buf.append(item_b[1])
            total_benign += 1
            item_b = next(gen_b, None)
        else:
            buf.append(item_a[1])
            total_attacks += 1
            item_a = next(gen_a, None)
            
        total_written += 1
        
        if len(buf) >= args.chunk_size:
            writer.writerows(buf)
            buf.clear()
            
        if total_written % 10_000_000 == 0:
            el = time.time() - t_start_merge
            qps_proc = total_written / el if el > 0 else 0
            print(f"[progresso] {total_written:,} eventos estruturados ({el:.0f}s, {qps_proc:,.0f} ev/s) | "
                  f"Benigno: {total_benign:,} | Ataque: {total_attacks:,}", flush=True)
                  
    if buf:
        writer.writerows(buf)
        buf.clear()
        
    out_file.close()
    
    el_total = time.time() - t0_global
    file_size_bytes = os.path.getsize(target_path)
    
    manifest = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "arquivo_saida": target_path,
        "formato": "CSV_GZIP" if use_gzip else "CSV_TEXTO",
        "tamanho_bytes": file_size_bytes,
        "tamanho_gb": round(file_size_bytes / 1e9, 2),
        "total_eventos_estruturados": total_written,
        "total_eventos_benignos_label_0": total_benign,
        "total_eventos_ataque_label_1": total_attacks,
        "proporcao_benigno_pct": round((total_benign / total_written) * 100, 2) if total_written else 0,
        "proporcao_ataque_pct": round((total_attacks / total_written) * 100, 2) if total_written else 0,
        "amostra_inspecao": path_sample,
        "colunas": CSV_HEADER,
        "tempo_execucao_segundos": round(el_total, 2)
    }
    
    manifest_path = os.path.join(args.output_dir, "estruturacao_manifesto.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        
    print("\n" + "=" * 75)
    print(">>> RESUMO DA ESTRUTURAÇÃO TABULAR")
    print("=" * 75)
    print(f"Total de Eventos: {total_written:,}")
    print(f"  * Benignos (label = 0): {total_benign:,} ({manifest['proporcao_benigno_pct']}%)")
    print(f"  * Malignos (label = 1): {total_attacks:,} ({manifest['proporcao_ataque_pct']}%)")
    print(f"Arquivo Consolidado: {target_path} ({manifest['tamanho_gb']} GB)")
    print(f"Tempo Total: {el_total:.1f} segundos")
    print(f"Manifesto: {manifest_path}")
    print("Processamento concluído com sucesso!")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--benign", default=conf.BENIGN_LOG_PATH)
    parser.add_argument("--attacks", default=conf.ATTACK_LOG_PATH)
    parser.add_argument("--output-dir", default=conf.REFINED_DIR)
    parser.add_argument("--sample-size", type=int, default=100000, help="tamanho da amostra descompactada")
    parser.add_argument("--chunk-size", type=int, default=100000)
    parser.add_argument("--limit-benign", type=int, default=0, help="limite para testes rápidos (0 = todos)")
    parser.add_argument("--limit-attacks", type=int, default=0, help="limite para testes rápidos (0 = todos)")
    parser.add_argument("--no-compress", action="store_true", help="gera .csv puro sem compressão gzip")
    
    run_pipeline(parser.parse_args())


if __name__ == "__main__":
    main()
