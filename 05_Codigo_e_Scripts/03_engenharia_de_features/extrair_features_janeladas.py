#!/usr/bin/env python3
"""
Extracao de atributos estatisticos e lexicos em janelas deslizantes sobre logs DNS.
Calcula QPS, sequencia maxima de consoantes (C_max), entropia de Shannon (H),
comprimento medio do FQDN (L_mean) e razao de dominios unicos (U).
"""

import argparse
import collections
import csv
import gzip
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import conf


def shannon_entropy(domain_list):
    if not domain_list:
        return 0.0

    chars = []
    for d in domain_list:
        chars.extend(d.split(".")[0])

    if not chars:
        return 0.0

    n = len(chars)
    counts = collections.Counter(chars)
    h = 0.0
    for cnt in counts.values():
        p = cnt / n
        if p > 0.0:
            h -= p * math.log2(p)
    return round(h, 4)


def mean_max_consonant_streak(domain_list):
    if not domain_list:
        return 0.0

    vowels = conf.VOWELS
    total_streak = 0
    for d in domain_list:
        sub = d.split(".")[0].lower()
        cur = 0
        mx = 0
        for ch in sub:
            if "a" <= ch <= "z" and ch not in vowels:
                cur += 1
                if cur > mx:
                    mx = cur
            else:
                cur = 0
        total_streak += mx

    return round(total_streak / len(domain_list), 4)


def compute_window_features(window_id, start_epoch, end_epoch, events, dt_sec):
    n_total = len(events)
    if n_total == 0:
        return None

    domains = [e[5] for e in events]
    qps = round(n_total / dt_sec, 4)
    c_max = mean_max_consonant_streak(domains)
    entropy = shannon_entropy(domains)
    mean_fqdn_len = round(sum(len(d) for d in domains) / n_total, 2)
    unique_ratio = round(len(set(domains)) / n_total, 4)

    n_attack = sum(1 for e in events if e[9] == "1")
    n_benign = n_total - n_attack
    window_label = 1 if n_attack > 0 else 0
    attack_ratio = round(n_attack / n_total, 4)

    dt_iso = datetime.fromtimestamp(start_epoch, timezone.utc).strftime("%d-%b-%Y %H:%M:%S")

    return [
        window_id,
        dt_iso,
        f"{start_epoch:.3f}",
        f"{end_epoch:.3f}",
        qps,
        c_max,
        entropy,
        mean_fqdn_len,
        unique_ratio,
        n_total,
        n_benign,
        n_attack,
        attack_ratio,
        window_label,
    ]


def run_feature_extraction(args):
    t0 = time.time()
    os.makedirs(args.output_dir, exist_ok=True)
    out_csv = os.path.join(args.output_dir, f"dataset_features_48h_w{args.window_sec}s.csv")
    out_json = os.path.join(args.output_dir, f"features_manifesto_w{args.window_sec}s.json")

    header = [
        "window_id", "datetime", "start_epoch", "end_epoch",
        "qps", "max_consonant_streak", "entropy", "mean_fqdn_len", "unique_ratio",
        "total_queries", "benign_queries", "attack_queries", "attack_ratio", "label",
    ]

    open_fn = gzip.open if args.input.endswith(".gz") else open

    window_id = 0
    cur_window_start = None
    cur_events = []
    total_events_read = 0
    windows_generated = 0
    anomalous_windows = 0
    nominal_windows = 0

    with open_fn(args.input, "rt", encoding="utf-8") as f_in, \
         open(out_csv, "w", newline="", encoding="utf-8") as f_out:

        writer = csv.writer(f_out)
        writer.writerow(header)

        reader = csv.reader(f_in)
        next(reader, None)

        for row in reader:
            total_events_read += 1
            epoch = float(row[1])

            if cur_window_start is None:
                cur_window_start = epoch

            if epoch < cur_window_start + args.window_sec:
                cur_events.append(row)
            else:
                feat = compute_window_features(
                    window_id, cur_window_start, cur_window_start + args.window_sec,
                    cur_events, args.window_sec
                )
                if feat:
                    writer.writerow(feat)
                    windows_generated += 1
                    if feat[-1] == 1:
                        anomalous_windows += 1
                    else:
                        nominal_windows += 1
                    window_id += 1

                while epoch >= cur_window_start + args.window_sec:
                    cur_window_start += args.window_sec

                cur_events = [row]

        if cur_events:
            feat = compute_window_features(
                window_id, cur_window_start, cur_window_start + args.window_sec,
                cur_events, args.window_sec
            )
            if feat:
                writer.writerow(feat)
                windows_generated += 1
                if feat[-1] == 1:
                    anomalous_windows += 1
                else:
                    nominal_windows += 1

    el_total = time.time() - t0
    manifest = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "arquivo_entrada": args.input,
        "arquivo_saida": out_csv,
        "delta_t_segundos": args.window_sec,
        "total_eventos_processados": total_events_read,
        "total_janelas_geradas": windows_generated,
        "janelas_nominais_label_0": nominal_windows,
        "janelas_anomalas_label_1": anomalous_windows,
        "taxa_contaminacao_pct": round((anomalous_windows / windows_generated) * 100, 2) if windows_generated else 0,
        "tempo_execucao_s": round(el_total, 2),
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Extracao concluida em {el_total:.1f}s: {windows_generated} janelas salvas em {out_csv}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=conf.STRUCTURED_CSV_GZ)
    parser.add_argument("--output-dir", default=conf.FEATURES_DIR)
    parser.add_argument("--window-sec", type=int, default=conf.WINDOW_SIZE_SEC)
    run_feature_extraction(parser.parse_args())


if __name__ == "__main__":
    main()
