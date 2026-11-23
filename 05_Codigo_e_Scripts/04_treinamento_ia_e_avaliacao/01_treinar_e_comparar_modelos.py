#!/usr/bin/env python3
"""
Treinamento e avaliacao comparativa entre o modelo Baseline (Nadler et al., 2019)
e a Proposta deste TCC (com C_max) sobre o dataset oficial janelado de 48 horas.
"""

import json
import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import conf


def calcular_metricas(y_true, y_pred, scores, nome_modelo, desc_atributos):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    acc = (tp + tn) / len(y_true) * 100.0
    prec = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 0.0
    rec = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else 0.0
    far = (fp / (fp + tn) * 100.0) if (fp + tn) > 0 else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
    auc_roc = roc_auc_score(y_true, scores)
    auc_pr = average_precision_score(y_true, scores)
    return {
        "Abordagem": nome_modelo,
        "Atributos": desc_atributos,
        "Acurácia (%)": round(acc, 2),
        "Precisão (%)": round(prec, 2),
        "Recall (%)": round(rec, 2),
        "FAR (%)": round(far, 2),
        "Falsos Alarmes (FP)": int(fp),
        "Ataques Perdidos (FN)": int(fn),
        "F1-Score (%)": round(f1, 2),
        "ROC-AUC": round(auc_roc, 4),
        "PR-AUC": round(auc_pr, 4),
        "TP": int(tp),
        "TN": int(tn),
    }


def mapear_blocos_campanha(df_teste):
    campanha_ids = np.zeros(len(df_teste), dtype=int)
    labels = df_teste["label"].values
    cid = 0
    in_block = False
    for i, lbl in enumerate(labels):
        if lbl == 1:
            if not in_block:
                cid += 1
                in_block = True
            campanha_ids[i] = cid
        else:
            in_block = False
    return campanha_ids


def salvar_csv_duplo(df, nome_principal, nome_legado=None):
    os.makedirs(conf.RESULTS_TABLES_DIR, exist_ok=True)
    df.to_csv(os.path.join(conf.RESULTS_TABLES_DIR, nome_principal), index=False)


def main():
    os.makedirs(conf.RESULTS_DIR, exist_ok=True)
    os.makedirs(conf.RESULTS_FIGURES_DIR, exist_ok=True)
    os.makedirs(conf.RESULTS_TABLES_DIR, exist_ok=True)

    df = pd.read_csv(conf.DATASET_OFFICIAL_PATH)
    treino = df[df["window_id"] < conf.TRAIN_WINDOWS].copy()
    teste = df[df["window_id"] >= conf.TRAIN_WINDOWS].copy().reset_index(drop=True)
    y_teste = teste["label"].values

    features_nadler = conf.FEATURES_BASELINE
    features_proposta = conf.FEATURES_PROPOSED

    modelo_nadler = IsolationForest(
        n_estimators=conf.IF_N_ESTIMATORS,
        max_samples=conf.IF_MAX_SAMPLES,
        random_state=conf.SEED,
        n_jobs=conf.IF_N_JOBS,
    )
    modelo_nadler.fit(treino[features_nadler])

    modelo_proposta = IsolationForest(
        n_estimators=conf.IF_N_ESTIMATORS,
        max_samples=conf.IF_MAX_SAMPLES,
        random_state=conf.SEED,
        n_jobs=conf.IF_N_JOBS,
    )
    modelo_proposta.fit(treino[features_proposta])

    scores_treino_nadler = -modelo_nadler.decision_function(treino[features_nadler])
    scores_treino_proposta = -modelo_proposta.decision_function(treino[features_proposta])

    limiar_nadler = float(np.percentile(scores_treino_nadler, conf.THRESHOLD_PERCENTILE))
    limiar_proposta = float(np.percentile(scores_treino_proposta, conf.THRESHOLD_PERCENTILE))

    scores_teste_nadler = -modelo_nadler.decision_function(teste[features_nadler])
    scores_teste_proposta = -modelo_proposta.decision_function(teste[features_proposta])

    pred_nadler = (scores_teste_nadler >= limiar_nadler).astype(int)
    pred_proposta = (scores_teste_proposta >= limiar_proposta).astype(int)

    m_nadler = calcular_metricas(
        y_teste, pred_nadler, scores_teste_nadler,
        conf.MODEL_BASELINE_NAME,
        "4 [QPS, Entropia, Comp. Médio, Únicos]",
    )
    m_proposta = calcular_metricas(
        y_teste, pred_proposta, scores_teste_proposta,
        conf.MODEL_PROPOSED_NAME,
        "5 [QPS, C_max, Entropia, Comp. Médio, Únicos]",
    )

    cols_tabela = [
        "Abordagem", "Atributos", "Acurácia (%)", "Precisão (%)",
        "Recall (%)", "FAR (%)", "Falsos Alarmes (FP)", "Ataques Perdidos (FN)",
        "F1-Score (%)", "ROC-AUC", "PR-AUC",
    ]
    df_resumo = pd.DataFrame([m_nadler, m_proposta])[cols_tabela]
    salvar_csv_duplo(
        df_resumo,
        "tabela_01_resumo_comparativo_modelos.csv",
        "tabela_resumo_tcc_simplificada.csv",
    )

    teste_df = teste.copy()
    teste_df["pred_nadler"] = pred_nadler
    teste_df["pred_proposta"] = pred_proposta
    teste_df["campanha_id"] = mapear_blocos_campanha(teste_df)

    linhas_intensidade = []
    for nivel in ["LEVE", "MODERADO", "INTENSO"]:
        sub = teste_df[teste_df["nivel_ataque"] == nivel]
        tp_n = np.sum((sub["label"] == 1) & (sub["pred_nadler"] == 1))
        fn_n = np.sum((sub["label"] == 1) & (sub["pred_nadler"] == 0))
        tp_p = np.sum((sub["label"] == 1) & (sub["pred_proposta"] == 1))
        fn_p = np.sum((sub["label"] == 1) & (sub["pred_proposta"] == 0))
        rec_n = tp_n / len(sub) * 100.0 if len(sub) > 0 else 0.0
        rec_p = tp_p / len(sub) * 100.0 if len(sub) > 0 else 0.0

        linhas_intensidade.append({
            "Intensidade": nivel,
            "Total Janelas": len(sub),
            "Nadler Recall (%)": round(rec_n, 2),
            "Nadler Detectados": int(tp_n),
            "Nadler Perdidos (FN)": int(fn_n),
            "Kaio Recall (%)": round(rec_p, 2),
            "Kaio Detectados": int(tp_p),
            "Kaio Perdidos (FN)": int(fn_p),
            "Ganho Sensibilidade (%)": round(rec_p - rec_n, 2),
            "Ataques Salvos a Mais": int(fn_n - fn_p),
        })

    df_intensidade = pd.DataFrame(linhas_intensidade)
    salvar_csv_duplo(
        df_intensidade,
        "tabela_02_desempenho_por_intensidade.csv",
        "tabela_intensidade_ataque.csv",
    )

    # Tabela 3: Desempenho detalhado nas 21 campanhas individuais
    linhas_campanhas = []
    for cid in sorted(teste_df[teste_df["campanha_id"] > 0]["campanha_id"].unique()):
        sub_c = teste_df[teste_df["campanha_id"] == cid]
        nivel = sub_c["nivel_ataque"].mode().iloc[0]
        dt_ini = str(sub_c["datetime"].iloc[0])[12:17]
        dt_fim = str(sub_c["datetime"].iloc[-1])[12:17]
        dia_str = "07/Jun" if "07-Jun" in str(sub_c["datetime"].iloc[0]) else "08/Jun"
        qps_med = float(sub_c["qps"].mean())
        tp_n = int(np.sum(sub_c["pred_nadler"] == 1))
        tp_p = int(np.sum(sub_c["pred_proposta"] == 1))
        n_win = len(sub_c)
        rec_n = round(tp_n / n_win * 100.0, 2)
        rec_p = round(tp_p / n_win * 100.0, 2)
        linhas_campanhas.append({
            "Campanha": int(cid),
            "Data": dia_str,
            "Horario": f"{dt_ini}-{dt_fim}",
            "Nivel": nivel,
            "Janelas_30s": n_win,
            "QPS_Medio_Janela": round(qps_med, 1),
            "C_max_Medio": round(float(sub_c["max_consonant_streak"].mean()), 3),
            "Entropia_Media": round(float(sub_c["entropy"].mean()), 3),
            "Nadler_Detectados": tp_n,
            "Nadler_Recall_Pct": rec_n,
            "Proposta_Detectados": tp_p,
            "Proposta_Recall_Pct": rec_p,
            "Ganho_Pct": round(rec_p - rec_n, 2),
        })

    df_campanhas = pd.DataFrame(linhas_campanhas)
    salvar_csv_duplo(df_campanhas, "tabela_03_desempenho_por_campanha_21.csv")

    df_export_scores = pd.DataFrame({
        "window_id": teste["window_id"].values,
        "datetime": teste["datetime"].values,
        "start_epoch": teste["start_epoch"].values,
        "qps": teste["qps"].values,
        "max_consonant_streak": teste["max_consonant_streak"].values,
        "entropy": teste["entropy"].values,
        "mean_fqdn_len": teste["mean_fqdn_len"].values,
        "unique_ratio": teste["unique_ratio"].values,
        "label": y_teste,
        "nivel_ataque": teste["nivel_ataque"].values,
        "campanha_id": teste_df["campanha_id"].values,
        "score_nadler": scores_teste_nadler,
        "score_proposta": scores_teste_proposta,
        "pred_nadler": pred_nadler,
        "pred_proposta": pred_proposta,
        "limiar_nadler": limiar_nadler,
        "limiar_proposta": limiar_proposta,
    })
    salvar_csv_duplo(df_export_scores, "predicoes_e_scores_teste.csv")

    desc_stats = {}
    for feat in features_proposta:
        desc_stats[feat] = {
            "nominal_mean": round(float(df[df["label"] == 0][feat].mean()), 4),
            "nominal_std": round(float(df[df["label"] == 0][feat].std()), 4),
            "attack_mean": round(float(df[df["label"] == 1][feat].mean()), 4),
            "attack_std": round(float(df[df["label"] == 1][feat].std()), 4),
        }
    for d_out in [conf.RESULTS_DIR, conf.RESULTS_TABLES_DIR]:
        with open(os.path.join(d_out, "estatisticas_descritivas_features.json"), "w") as f:
            json.dump(desc_stats, f, indent=2)

    epochs_hours = (df["start_epoch"] - df["start_epoch"].iloc[0]) / 3600.0
    report_data = {
        "res_base": m_nadler,
        "res_prop": m_proposta,
        "intensidade": linhas_intensidade,
        "campanhas": linhas_campanhas,
        "limiar_nadler": round(limiar_nadler, 4),
        "limiar_proposta": round(limiar_proposta, 4),
        "total_windows": len(df),
        "total_nominal": int(sum(df["label"] == 0)),
        "total_attack": int(sum(df["label"] == 1)),
        "timeline_sample": {
            "hours": epochs_hours[::10].round(2).tolist(),
            "qps": df["qps"][::10].round(1).tolist(),
            "cmax": df["max_consonant_streak"][::10].round(4).tolist(),
            "entropy": df["entropy"][::10].round(2).tolist(),
            "label": df["label"][::10].tolist(),
        },
    }
    for d_out in [conf.RESULTS_DIR, conf.RESULTS_TABLES_DIR]:
        with open(os.path.join(d_out, "dados_relatorio_consolidado.json"), "w") as f:
            json.dump(report_data, f, indent=2)

    print("\nResumo de Desempenho no Conjunto de Teste:")
    print(df_resumo.to_string(index=False))
    print("\nDesempenho por Intensidade de Ataque:")
    print(df_intensidade.to_string(index=False))
    print(f"\nTabelas salvas em:\n  - {conf.RESULTS_TABLES_DIR}")


if __name__ == "__main__":
    main()
