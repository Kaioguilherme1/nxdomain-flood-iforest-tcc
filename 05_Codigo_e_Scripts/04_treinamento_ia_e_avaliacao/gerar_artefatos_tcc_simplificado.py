#!/usr/bin/env python3
"""
Script unificado e simplificado para reproduzir exatamente as 4 Figuras e as
3 Tabelas de resultados experimentais (Tabelas 3, 4 e 5) presentes no texto final do TCC.

Entrada:
    06_Datasets_e_Logs/03_dataset_final_features/dataset_features_48h_w30s.csv

Saida:
    07_Resultados_e_Relatorios/03_Artefatos_Finais_TCC/
        - Figura_1_mecanismo_isolamento.png
        - Figura_2_matrizes_confusao.png
        - Figura_3_recall_por_intensidade.png
        - Figura_4_diluicao_diurna_ataque_leve.png
        - Tabela_3_campanhas_ataque.csv
        - Tabela_4_desempenho_global.csv
        - Tabela_5_atributos_por_intensidade.csv
"""

import importlib.util
import os
import shutil
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score

# Importa configuracoes oficiais do projeto (conf.py)
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)
import conf

OUT_DIR = os.path.join(conf.RESULTS_DIR, "03_Artefatos_Finais_TCC")
COR_BASELINE = "#64748b"
COR_PROPOSTA = "#1e40af"


def treinar_e_avaliar(df):
    """Separa as 20h iniciais (treino One-Class) das 28h seguintes (teste) e treina os dois modelos."""
    treino = df[df["window_id"] < conf.TRAIN_WINDOWS].copy()
    teste = df[df["window_id"] >= conf.TRAIN_WINDOWS].copy().reset_index(drop=True)

    modelos = {
        "nadler": conf.FEATURES_BASELINE,
        "proposta": conf.FEATURES_PROPOSED,
    }
    for chave, feats in modelos.items():
        clf = IsolationForest(
            n_estimators=conf.IF_N_ESTIMATORS,
            max_samples=conf.IF_MAX_SAMPLES,
            random_state=conf.SEED,
            n_jobs=conf.IF_N_JOBS,
        )
        clf.fit(treino[feats])
        scores_treino = -clf.decision_function(treino[feats])
        limiar = float(np.percentile(scores_treino, conf.THRESHOLD_PERCENTILE))
        scores_teste = -clf.decision_function(teste[feats])

        teste[f"score_{chave}"] = scores_teste
        teste[f"limiar_{chave}"] = limiar
        teste[f"pred_{chave}"] = (scores_teste >= limiar).astype(int)

    return teste


def gerar_tabela_3(teste):
    """Tabela 3: Parametrizacao e carga efetiva integrada das 21 campanhas por intensidade."""
    specs = [
        ("LEVE", "Leve", "600 s (10 min)", "10 clientes", "1.000 QPS", 11),
        ("MODERADO", "Moderado", "900 s (15 min)", "40 clientes", "5.000 QPS", 6),
        ("INTENSO", "Intenso", "1.800 s (30 min)", "100 clientes", "20.000 QPS", 4),
    ]
    linhas = []
    for chave, rotulo, duracao, clientes, teto, n_camp in specs:
        sub = teste[teste["nivel_ataque"] == chave]
        q_min = int(sub["attack_queries"].min())
        q_max = int(sub["attack_queries"].max())
        qps_med = float(sub["attack_queries"].mean() / conf.WINDOW_SIZE_SEC)
        linhas.append({
            "Nível de Intensidade": rotulo,
            "Duração (-l)": duracao,
            "Clientes (-c)": clientes,
            "Teto dnsperf (-Q)": teto,
            "Carga Efetiva Integrada (Δt = 30 s)": f"{q_min}–{q_max} cons./jan. (μ = {qps_med:.2f} QPS)",
            "Campanhas": f"{n_camp} campanhas",
            "Janelas (Δt = 30 s)": f"{len(sub)} janelas",
        })
    total_atk = int(teste[teste["label"] == 1]["attack_queries"].sum())
    linhas.append({
        "Nível de Intensidade": "Total Consolidado",
        "Duração (-l)": "—",
        "Clientes (-c)": "—",
        "Teto dnsperf (-Q)": "—",
        "Carga Efetiva Integrada (Δt = 30 s)": f"{total_atk:,} consultas de ataque".replace(",", "."),
        "Campanhas": "21 campanhas",
        "Janelas (Δt = 30 s)": f"{int((teste['label'] == 1).sum())} janelas",
    })
    df_t3 = pd.DataFrame(linhas)
    df_t3.to_csv(os.path.join(OUT_DIR, "Tabela_3_campanhas_ataque.csv"), index=False)
    return df_t3


def gerar_tabela_4(teste):
    """Tabela 4: Comparativo global de metricas (Baseline vs. Proposta com C_max)."""
    y_true = teste["label"].values

    def metricas(chave):
        y_pred = teste[f"pred_{chave}"].values
        scores = teste[f"score_{chave}"].values
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        acc = (tp + tn) / len(y_true) * 100.0
        prec = tp / (tp + fp) * 100.0
        rec = tp / (tp + fn) * 100.0
        far = fp / (fp + tn) * 100.0
        f1 = 2 * prec * rec / (prec + rec)
        return {
            "acc": acc, "prec": prec, "rec": rec, "f1": f1, "far": far,
            "fp": int(fp), "fn": int(fn),
            "roc": roc_auc_score(y_true, scores),
            "pr": average_precision_score(y_true, scores),
        }

    b = metricas("nadler")
    p = metricas("proposta")
    linhas = [
        ("Atributos de Entrada", "4 (QPS, H, L, U)", "5 (QPS, C_max, H, L, U)", "+1 atributo"),
        ("Acurácia Global (%)", f"{b['acc']:.2f}%", f"{p['acc']:.2f}%", f"{p['acc'] - b['acc']:+.2f} p.p."),
        ("Precisão (%)", f"{b['prec']:.2f}%", f"{p['prec']:.2f}%", f"{p['prec'] - b['prec']:+.2f} p.p."),
        ("Recall / Taxa de Detecção (%)", f"{b['rec']:.2f}%", f"{p['rec']:.2f}%", f"{p['rec'] - b['rec']:+.2f} p.p."),
        ("F1-Score (%)", f"{b['f1']:.2f}%", f"{p['f1']:.2f}%", f"{p['f1'] - b['f1']:+.2f} p.p."),
        ("Taxa de Falsos Alarmes - FAR (%)", f"{b['far']:.2f}%", f"{p['far']:.2f}%", f"{p['far'] - b['far']:+.2f} p.p."),
        ("Falsos Alarmes (FP)", f"{b['fp']} janelas", f"{p['fp']} janelas", f"{p['fp'] - b['fp']:+d} janela"),
        ("Ataques Perdidos (FN)", f"{b['fn']} janelas", f"{p['fn']} janelas", f"{p['fn'] - b['fn']:+d} janelas"),
        ("Área sob a Curva ROC (AUC-ROC)", f"{b['roc']:.4f}", f"{p['roc']:.4f}", f"{p['roc'] - b['roc']:+.4f}"),
        ("Área sob a Curva PR (AUC-PR)", f"{b['pr']:.4f}", f"{p['pr']:.4f}", f"{p['pr'] - b['pr']:+.4f}"),
    ]
    df_t4 = pd.DataFrame(linhas, columns=["Métrica Avaliada", "Baseline (Nadler et al., 2019)", "Proposta deste TCC (com C_max)", "Variação Absoluta"])
    df_t4.to_csv(os.path.join(OUT_DIR, "Tabela_4_desempenho_global.csv"), index=False)
    return b, p


def gerar_tabela_5(teste):
    """Tabela 5: Medias dos 5 atributos (Normal: media +- dp; Ataques: media e Delta%)."""
    nom = teste[teste["nivel_ataque"] == "NOMINAL"]
    atributos = [
        ("qps", "Consultas por Segundo (QPS)", 2, ""),
        ("max_consonant_streak", "Consoantes Consecutivas (C_max)", 2, ""),
        ("entropy", "Entropia de Shannon (H)", 2, " bits"),
        ("mean_fqdn_len", "Comprimento Médio (L)", 2, " carac."),
        ("unique_ratio", "Razão de Domínios Únicos (U)", 3, ""),
    ]
    linhas = []
    for col, rotulo, casas, unid in atributos:
        m_nom = float(nom[col].mean())
        dp_nom = float(nom[col].std())
        m_str = f"{m_nom:.{casas}f}".replace(".", ",")
        dp_str = f"{dp_nom:.{casas}f}".replace(".", ",")
        row = {
            "Atributo Calculado (Δt = 30 s)": rotulo,
            "Tráfego Normal (2.699 jan.)": f"{m_str} ± {dp_str}{unid}",
        }
        for nivel, col_nome in [("LEVE", "Ataque Leve (231 jan.)"), ("MODERADO", "Ataque Moderado (186 jan.)"), ("INTENSO", "Ataque Intenso (244 jan.)")]:
            m_atk = float(teste[teste["nivel_ataque"] == nivel][col].mean())
            delta = (m_atk - m_nom) / m_nom * 100.0
            atk_str = f"{m_atk:.{casas}f}".replace(".", ",")
            delta_str = f"{delta:+.1f}%".replace(".", ",")
            row[col_nome] = f"{atk_str}{unid} ({delta_str})"
        linhas.append(row)

    df_t5 = pd.DataFrame(linhas)
    df_t5.to_csv(os.path.join(OUT_DIR, "Tabela_5_atributos_por_intensidade.csv"), index=False)
    return df_t5


def gerar_figura_1():
    """Figura 1: Mecanismo de isolamento da arvore (reutiliza script dedicado)."""
    spec = importlib.util.spec_from_file_location(
        "mod_fig1",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "03_gerar_figura_arvore_isolamento.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.gerar_figura_arvore()
    origem = os.path.join(conf.RESULTS_FIGURES_DIR, "Figura_01_mecanismo_isolamento_itree.png")
    shutil.copy2(origem, os.path.join(OUT_DIR, "Figura_1_mecanismo_isolamento.png"))


def gerar_figura_2(teste, met_b, met_p):
    """Figura 2: Matrizes de confusao (Baseline vs. Proposta)."""
    y_true = teste["label"].values
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.6), dpi=conf.PLOT_DPI)
    configs = [
        (axes[0], "pred_nadler", f"{conf.MODEL_BASELINE_NAME}\nRecall = {met_b['rec']:.2f}% | FAR = {met_b['far']:.2f}% (FN = {met_b['fn']})"),
        (axes[1], "pred_proposta", f"Proposta deste TCC (com $C_{{max}}$)\nRecall = {met_p['rec']:.2f}% | FAR = {met_p['far']:.2f}% (FN = {met_p['fn']})"),
    ]
    nomes = [["Verdadeiro Negativo (VN)", "Falso Positivo (FP)"], ["Falso Negativo (FN)", "Verdadeiro Positivo (VP)"]]
    for ax, col_pred, titulo in configs:
        cm = confusion_matrix(y_true, teste[col_pred].values)
        pct = cm / cm.sum(axis=1, keepdims=True) * 100.0
        annot = np.array([[f"{nomes[i][j]}\n{cm[i, j]} ({pct[i, j]:.2f}%)" for j in range(2)] for i in range(2)])
        sns.heatmap(
            cm, annot=annot, fmt="", cmap="Blues", cbar=False, ax=ax,
            xticklabels=["Nominal (0)", "Anômalo (1)"], yticklabels=["Nominal (0)", "Anômalo (1)"],
            annot_kws={"size": 9.5, "weight": "bold"}, linewidths=1.0, linecolor="#cbd5e1",
        )
        ax.set_title(titulo, fontsize=10.5, fontweight="bold", pad=10)
        ax.set_xlabel("Classe Predita pelo Modelo", fontsize=10, fontweight="bold")
        ax.set_ylabel("Classe Real (Ground Truth)", fontsize=10, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "Figura_2_matrizes_confusao.png"), dpi=conf.PLOT_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def gerar_figura_3(teste, met_b, met_p):
    """Figura 3: Recall estratificado por nivel de intensidade do ataque."""
    niveis = ["LEVE", "MODERADO", "INTENSO"]
    val_b = [float(teste[teste["nivel_ataque"] == n]["pred_nadler"].mean() * 100.0) for n in niveis] + [met_b["rec"]]
    val_p = [float(teste[teste["nivel_ataque"] == n]["pred_proposta"].mean() * 100.0) for n in niveis] + [met_p["rec"]]
    categorias = ["Ataque Leve\n(231 janelas)", "Ataque Moderado\n(186 janelas)", "Ataque Intenso\n(244 janelas)", "Média Global\n(661 janelas)"]

    x, w = np.arange(len(categorias)), 0.34
    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=conf.PLOT_DPI)
    b1 = ax.bar(x - w / 2, val_b, w, label=conf.MODEL_BASELINE_NAME, color=COR_BASELINE, edgecolor="#1e293b", lw=0.8, zorder=3)
    b2 = ax.bar(x + w / 2, val_p, w, label="Proposta deste TCC (com $C_{max}$)", color=COR_PROPOSTA, edgecolor="#0f172a", lw=0.8, zorder=3)

    for bars, cor in [(b1, "#334155"), (b2, "#1e3a8a")]:
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom", fontsize=9.5, color=cor, fontweight="bold")

    ax.set_ylabel("Taxa de Detecção / Recall (%)", fontsize=10.5, fontweight="bold")
    ax.set_title("Taxa de Detecção (Recall) por Nível de Intensidade de Ataque", fontsize=11.5, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(categorias, fontsize=9.5, fontweight="bold")
    ax.set_ylim(50, 110)
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=9.5)
    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "Figura_3_recall_por_intensidade.png"), dpi=conf.PLOT_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def gerar_figura_4(teste):
    """Figura 4: Impacto da diluicao diurna nos ataques leves por periodo do dia."""
    leve = teste[teste["nivel_ataque"] == "LEVE"].copy()
    horas = pd.to_datetime(leve["start_epoch"], unit="s").dt.hour
    leve["periodo"] = np.where(
        horas <= 6, "Madrugada (00h–06h)\n[Baixo Tráfego: ~305 QPS]",
        np.where((horas >= 8) & (horas <= 17), "Horário Comercial (08h–17h)\n[Pico Diurno: ~840 QPS]",
                 "Transição de Turno (07h e 18h–23h)\n[Tráfego Intermediário: ~590 QPS]")
    )
    ordem = [
        "Madrugada (00h–06h)\n[Baixo Tráfego: ~305 QPS]",
        "Transição de Turno (07h e 18h–23h)\n[Tráfego Intermediário: ~590 QPS]",
        "Horário Comercial (08h–17h)\n[Pico Diurno: ~840 QPS]",
    ]
    rec_b = [float(leve[leve["periodo"] == p]["pred_nadler"].mean() * 100.0) for p in ordem]
    rec_p = [float(leve[leve["periodo"] == p]["pred_proposta"].mean() * 100.0) for p in ordem]

    x, w = np.arange(len(ordem)), 0.34
    fig, ax = plt.subplots(figsize=(8.8, 5.0), dpi=conf.PLOT_DPI)
    b1 = ax.bar(x - w / 2, rec_b, w, label=conf.MODEL_BASELINE_NAME, color=COR_BASELINE, edgecolor="#1e293b", lw=0.8, zorder=3)
    b2 = ax.bar(x + w / 2, rec_p, w, label="Proposta deste TCC (com $C_{max}$)", color=COR_PROPOSTA, edgecolor="#0f172a", lw=0.8, zorder=3)

    for bars, cor in [(b1, "#334155"), (b2, "#1e3a8a")]:
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom", fontsize=9.5, color=cor, fontweight="bold")

    ax.set_ylabel("Taxa de Detecção em Ataques Leves — Recall (%)", fontsize=10, fontweight="bold")
    ax.set_title("Impacto do Volume de Tráfego Legítimo na Detecção de Ataques Leves", fontsize=11.2, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(ordem, fontsize=9.2, fontweight="bold")
    ax.set_ylim(0, 114)
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=9.2)
    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "Figura_4_diluicao_diurna_ataque_leve.png"), dpi=conf.PLOT_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    plt.rcParams["font.sans-serif"] = conf.FONT_FAMILY
    plt.rcParams["axes.edgecolor"] = "#334155"
    plt.rcParams["axes.linewidth"] = 0.8

    df = pd.read_csv(conf.DATASET_OFFICIAL_PATH)
    teste = treinar_e_avaliar(df)

    gerar_tabela_3(teste)
    met_b, met_p = gerar_tabela_4(teste)
    gerar_tabela_5(teste)

    gerar_figura_1()
    gerar_figura_2(teste, met_b, met_p)
    gerar_figura_3(teste, met_b, met_p)
    gerar_figura_4(teste)

    print(f"Artefatos do TCC gerados com sucesso em:\n  {OUT_DIR}")
    for arq in sorted(os.listdir(OUT_DIR)):
        print(f"  - {arq}")


if __name__ == "__main__":
    main()
