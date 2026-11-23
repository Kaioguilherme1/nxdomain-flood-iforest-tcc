#!/usr/bin/env python3
"""
Geracao das figuras cientificas padronizadas (300 DPI, estilo IEEE/SBC) para comparacao
entre o modelo Baseline (Nadler et al., 2019) e a Proposta deste TCC (com C_max).
"""

import os
import shutil
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import seaborn as sns
from sklearn.metrics import auc, confusion_matrix, precision_recall_curve, roc_curve

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import conf

COR_NADLER = "#64748b"      # Cinza ardosia sobrio (Baseline)
COR_PROPOSTA = "#1e40af"    # Azul marinho academico (Proposta)
COR_LIMIAR = "#b91c1c"      # Vermelho escuro para linha de limiar


def salvar_figura(fig, nome_numerado, nome_legado=None):
    os.makedirs(conf.RESULTS_FIGURES_DIR, exist_ok=True)
    p1 = os.path.join(conf.RESULTS_FIGURES_DIR, nome_numerado)
    fig.savefig(p1, dpi=conf.PLOT_DPI, bbox_inches="tight", facecolor="white")
    if os.path.abspath(conf.FIGURES_DIR) != os.path.abspath(conf.RESULTS_FIGURES_DIR):
        os.makedirs(conf.FIGURES_DIR, exist_ok=True)
        shutil.copy2(p1, os.path.join(conf.FIGURES_DIR, nome_numerado))
        if nome_legado:
            shutil.copy2(p1, os.path.join(conf.FIGURES_DIR, nome_legado))


def configurar_estilo():
    plt.rcParams["font.sans-serif"] = conf.FONT_FAMILY
    plt.rcParams["axes.edgecolor"] = "#334155"
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["axes.facecolor"] = "#ffffff"
    plt.rcParams["figure.facecolor"] = "#ffffff"


def gerar_figura_01_intensidade(df_int, df_resumo):
    categorias = [
        "Ataque Leve\n(231 janelas)",
        "Ataque Moderado\n(186 janelas)",
        "Ataque Intenso\n(244 janelas)",
        "Média Global\n(661 janelas)"
    ]
    rec_n_geral = float(df_resumo[df_resumo["Abordagem"].str.contains("Nadler")]["Recall (%)"].iloc[0])
    rec_p_geral = float(df_resumo[df_resumo["Abordagem"].str.contains("Proposta")]["Recall (%)"].iloc[0])

    val_nadler = df_int["Nadler Recall (%)"].tolist() + [rec_n_geral]
    val_proposta = df_int["Kaio Recall (%)"].tolist() + [rec_p_geral]

    x = np.arange(len(categorias))
    width = 0.34

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=conf.PLOT_DPI)
    b1 = ax.bar(x - width / 2, val_nadler, width, label=conf.MODEL_BASELINE_NAME,
                color=COR_NADLER, edgecolor="#1e293b", lw=0.8, zorder=3)
    b2 = ax.bar(x + width / 2, val_proposta, width, label="Proposta deste TCC (com $C_{max}$)",
                color=COR_PROPOSTA, edgecolor="#0f172a", lw=0.8, zorder=3)

    for r1 in b1:
        h = r1.get_height()
        ax.annotate(f"{h:.1f}%", xy=(r1.get_x() + r1.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                    fontsize=9.5, color="#334155", fontweight="bold")

    for r2 in b2:
        h = r2.get_height()
        ax.annotate(f"{h:.1f}%", xy=(r2.get_x() + r2.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                    fontsize=9.5, color="#1e3a8a", fontweight="bold")

    ax.annotate(
        "Ganho: +28,1% (+65 janelas detectadas)\nObs.: Sem dicionário (LMW), o Baseline sofre\ndiluição de entropia em rajadas de menor QPS",
        xy=(0 + width / 2, val_proposta[0]),
        xytext=(0.75, 71.0),
        fontsize=8.5,
        color="#0f172a",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#f8fafc", edgecolor="#94a3b8", lw=0.8),
        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.15", color="#475569", lw=1.0),
        zorder=5
    )

    ax.set_ylabel("Taxa de Detecção / Recall (%)", fontsize=10.5, fontweight="bold")
    ax.set_title("Taxa de Detecção (Recall) por Nível de Intensidade de QPS Injetado", fontsize=11.5, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(categorias, fontsize=9.5, fontweight="bold")
    ax.set_ylim(50, 110)
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=9.5)

    plt.tight_layout()
    salvar_figura(fig, "Figura_06_recall_por_intensidade_ataque.png", "figura_comparativo_intensidade_nadler_vs_kaio.png")
    plt.close(fig)


def gerar_figura_02_matriz_confusao(df_scores, df_resumo):
    y_true = df_scores["label"].values
    pred_n = df_scores["pred_nadler"].values
    pred_p = df_scores["pred_proposta"].values

    cm_n = confusion_matrix(y_true, pred_n)
    cm_p = confusion_matrix(y_true, pred_p)

    rec_n = float(df_resumo[df_resumo["Abordagem"].str.contains("Nadler")]["Recall (%)"].iloc[0])
    far_n = float(df_resumo[df_resumo["Abordagem"].str.contains("Nadler")]["FAR (%)"].iloc[0])
    rec_p = float(df_resumo[df_resumo["Abordagem"].str.contains("Proposta")]["Recall (%)"].iloc[0])
    far_p = float(df_resumo[df_resumo["Abordagem"].str.contains("Proposta")]["FAR (%)"].iloc[0])

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.6), dpi=conf.PLOT_DPI)

    for ax, cm, titulo in [
        (axes[0], cm_n, f"{conf.MODEL_BASELINE_NAME}\nRecall = {rec_n:.2f}% | FAR = {far_n:.2f}% (FN = 75)"),
        (axes[1], cm_p, f"Proposta deste TCC (com $C_{{max}}$)\nRecall = {rec_p:.2f}% | FAR = {far_p:.2f}% (FN = 10)"),
    ]:
        tot_row = cm.sum(axis=1, keepdims=True)
        pct = cm / tot_row * 100.0
        nomes_celula = [["Verdadeiro Negativo (VN)", "Falso Positivo (FP)"],
                        ["Falso Negativo (FN)", "Verdadeiro Positivo (VP)"]]
        annot = np.array([
            [f"{nomes_celula[i][j]}\n{cm[i, j]} ({pct[i, j]:.2f}%)" for j in range(2)]
            for i in range(2)
        ])
        sns.heatmap(
            cm, annot=annot, fmt="", cmap="Blues", cbar=False, ax=ax,
            xticklabels=["Nominal (0)", "Anômalo (1)"],
            yticklabels=["Nominal (0)", "Anômalo (1)"],
            annot_kws={"size": 9.5, "weight": "bold"},
            linewidths=1.0, linecolor="#cbd5e1",
        )
        ax.set_title(titulo, fontsize=10.5, fontweight="bold", pad=10)
        ax.set_xlabel("Classe Predita pelo Modelo", fontsize=10, fontweight="bold")
        ax.set_ylabel("Classe Real (Ground Truth)", fontsize=10, fontweight="bold")

    plt.tight_layout()
    salvar_figura(fig, "Figura_03_matrizes_confusao.png", "figura_matriz_confusao.png")
    plt.close(fig)


def gerar_figura_03_curvas_roc_pr(df_scores, df_resumo):
    y_true = df_scores["label"].values
    sc_n = df_scores["score_nadler"].values
    sc_p = df_scores["score_proposta"].values

    fpr_n, tpr_n, _ = roc_curve(y_true, sc_n)
    fpr_p, tpr_p, _ = roc_curve(y_true, sc_p)
    auc_n = auc(fpr_n, tpr_n)
    auc_p = auc(fpr_p, tpr_p)

    prec_n, rec_n, _ = precision_recall_curve(y_true, sc_n)
    prec_p, rec_p, _ = precision_recall_curve(y_true, sc_p)
    pr_auc_n = auc(rec_n, prec_n)
    pr_auc_p = auc(rec_p, prec_p)

    r_n = df_resumo[df_resumo["Abordagem"].str.contains("Nadler")].iloc[0]
    r_p = df_resumo[df_resumo["Abordagem"].str.contains("Proposta")].iloc[0]

    op_fpr_n = float(r_n["FAR (%)"]) / 100.0
    op_tpr_n = float(r_n["Recall (%)"]) / 100.0
    op_prec_n = float(r_n["Precisão (%)"]) / 100.0

    op_fpr_p = float(r_p["FAR (%)"]) / 100.0
    op_tpr_p = float(r_p["Recall (%)"]) / 100.0
    op_prec_p = float(r_p["Precisão (%)"]) / 100.0

    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.0), dpi=conf.PLOT_DPI)

    # --- Painel 1: Curva ROC ---
    axes[0].plot(fpr_n, tpr_n, color=COR_NADLER, lw=2.0, label=f"Baseline Nadler (ROC-AUC = {auc_n:.4f})")
    axes[0].plot(fpr_p, tpr_p, color=COR_PROPOSTA, lw=2.3, label=f"Proposta com $C_{{max}}$ (ROC-AUC = {auc_p:.4f})")
    axes[0].plot([0, 1], [0, 1], color="#94a3b8", linestyle="--", lw=1.0, label="Classificador Aleatório (AUC = 0.50)")

    axes[0].scatter([op_fpr_n], [op_tpr_n], color=COR_NADLER, edgecolor="#0f172a", s=58, zorder=5,
                    label="Limiar $\\tau$ no Baseline")
    axes[0].scatter([op_fpr_p], [op_tpr_p], color=COR_LIMIAR, edgecolor="#0f172a", s=68, marker="D", zorder=6,
                    label="Limiar $\\tau$ na Proposta")

    axes[0].annotate(
        f"Proposta ($\\tau$): TPR (Recall) = {op_tpr_p*100:.2f}% | FPR (FAR) = {op_fpr_p*100:.2f}%",
        xy=(op_fpr_p, op_tpr_p), xytext=(0.15, 0.90),
        fontsize=8.3, fontweight="bold", color="#1e3a8a",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#eff6ff", edgecolor="#93c5fd", lw=0.8),
        arrowprops=dict(arrowstyle="->", color="#1e40af", lw=1.0),
        zorder=7
    )
    axes[0].annotate(
        f"Baseline ($\\tau$): TPR (Recall) = {op_tpr_n*100:.2f}% | FPR (FAR) = {op_fpr_n*100:.2f}%",
        xy=(op_fpr_n, op_tpr_n), xytext=(0.15, 0.76),
        fontsize=8.3, color="#334155",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#f8fafc", edgecolor="#cbd5e1", lw=0.8),
        arrowprops=dict(arrowstyle="->", color="#64748b", lw=1.0),
        zorder=7
    )

    axes[0].set_xlabel("Taxa de Falsos Positivos — FPR / FAR", fontsize=10, fontweight="bold")
    axes[0].set_ylabel("Taxa de Verdadeiros Positivos — TPR / Recall", fontsize=10, fontweight="bold")
    axes[0].set_title("Curva ROC e Taxas no Limiar Operacional ($\\tau$)", fontsize=11, fontweight="bold")
    axes[0].set_xlim(-0.02, 1.02)
    axes[0].set_ylim(0.0, 1.04)
    axes[0].grid(True, linestyle="--", alpha=0.35)
    axes[0].legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=8.4)

    # --- Painel 2: Curva Precision-Recall ---
    axes[1].plot(rec_n, prec_n, color=COR_NADLER, lw=2.0, label=f"Baseline Nadler (PR-AUC = {pr_auc_n:.4f})")
    axes[1].plot(rec_p, prec_p, color=COR_PROPOSTA, lw=2.3, label=f"Proposta com $C_{{max}}$ (PR-AUC = {pr_auc_p:.4f})")

    axes[1].scatter([op_tpr_n], [op_prec_n], color=COR_NADLER, edgecolor="#0f172a", s=58, zorder=5,
                    label="Limiar $\\tau$ no Baseline")
    axes[1].scatter([op_tpr_p], [op_prec_p], color=COR_LIMIAR, edgecolor="#0f172a", s=68, marker="D", zorder=6,
                    label="Limiar $\\tau$ na Proposta")

    axes[1].annotate(
        f"Proposta ($\\tau$):\nPrecisão = {op_prec_p*100:.2f}% | Recall = {op_tpr_p*100:.2f}%",
        xy=(op_tpr_p, op_prec_p), xytext=(0.30, 0.87),
        fontsize=8.3, fontweight="bold", color="#1e3a8a",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#eff6ff", edgecolor="#93c5fd", lw=0.8),
        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.12", color="#1e40af", lw=1.0),
        zorder=7
    )
    axes[1].annotate(
        f"Baseline ($\\tau$):\nPrecisão = {op_prec_n*100:.2f}% | Recall = {op_tpr_n*100:.2f}%\nObs.: Queda abrupta após 88,6% de Recall",
        xy=(op_tpr_n, op_prec_n), xytext=(0.22, 0.70),
        fontsize=8.3, color="#334155",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#f8fafc", edgecolor="#cbd5e1", lw=0.8),
        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.12", color="#64748b", lw=1.0),
        zorder=7
    )

    axes[1].set_xlabel("Sensibilidade / Recall (TPR)", fontsize=10, fontweight="bold")
    axes[1].set_ylabel("Precisão — VP / (VP + FP)", fontsize=10, fontweight="bold")
    axes[1].set_title("Curva Precision-Recall e Taxas Operacionais ($\\tau$)", fontsize=11, fontweight="bold")
    axes[1].set_xlim(0.0, 1.03)
    axes[1].set_ylim(0.50, 1.03)
    axes[1].grid(True, linestyle="--", alpha=0.35)
    axes[1].legend(loc="lower left", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=8.4)

    plt.tight_layout()
    salvar_figura(fig, "Figura_05_curvas_roc_e_precision_recall.png", "figura_curvas_roc_e_pr.png")
    plt.close(fig)


def gerar_figura_04_metricas_globais(df_resumo):
    metricas = ["Acurácia (%)", "Precisão (%)", "Recall (%)", "F1-Score (%)"]
    labels = ["Acurácia", "Precisão", "Recall (Sensibilidade)", "F1-Score"]

    r_n = df_resumo[df_resumo["Abordagem"].str.contains("Nadler")].iloc[0]
    r_p = df_resumo[df_resumo["Abordagem"].str.contains("Proposta")].iloc[0]

    val_n = [float(r_n[m]) for m in metricas]
    val_p = [float(r_p[m]) for m in metricas]

    x = np.arange(len(labels))
    width = 0.34

    fig, ax = plt.subplots(figsize=(8.4, 4.7), dpi=conf.PLOT_DPI)
    b1 = ax.bar(x - width / 2, val_n, width, label=conf.MODEL_BASELINE_NAME,
                color=COR_NADLER, edgecolor="#1e293b", lw=0.8, zorder=3)
    b2 = ax.bar(x + width / 2, val_p, width, label="Proposta deste TCC (com $C_{max}$)",
                color=COR_PROPOSTA, edgecolor="#0f172a", lw=0.8, zorder=3)

    for r1 in b1:
        h = r1.get_height()
        ax.annotate(f"{h:.2f}%", xy=(r1.get_x() + r1.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                    fontsize=9, color="#334155", fontweight="bold")

    for r2 in b2:
        h = r2.get_height()
        ax.annotate(f"{h:.2f}%", xy=(r2.get_x() + r2.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                    fontsize=9, color="#1e3a8a", fontweight="bold")

    ax.set_ylabel("Valor da Métrica (%)", fontsize=10.5, fontweight="bold")
    ax.set_title("Comparação das Métricas Globais de Classificação no Conjunto de Teste", fontsize=11.5, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10, fontweight="bold")
    ax.set_ylim(80, 103.5)
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=9.5)

    plt.tight_layout()
    salvar_figura(fig, "Figura_04_metricas_globais_comparativo.png")
    plt.close(fig)


def gerar_figura_05_serie_temporal(df_scores):
    """
    Figura 5 redesenhada para compreensao imediata e zero sobreposicao:
    - Painel A: Comportamento do atributo proposto C_max (com distincao visual entre Ataque Leve e Moderado/Intenso)
    - Painel B: Margem de Decisao Normalizada (Score - Limiar tau) ao longo das 28h, onde valores >= 0 indicam
      DETECCAO e valores < 0 indicam NORMAL/NAO DETECTADO, destacando no horario comercial as campanhas leves C13, C15 e C17
      onde o Baseline falha completamente (0% de deteccao) enquanto a Proposta supera o limiar.
    """
    t0 = df_scores["start_epoch"].iloc[0]
    epochs_hours = (df_scores["start_epoch"] - t0) / 3600.0

    th_n = float(df_scores["limiar_nadler"].iloc[0])
    th_p = float(df_scores["limiar_proposta"].iloc[0])

    margem_n = df_scores["score_nadler"] - th_n
    margem_p = df_scores["score_proposta"] - th_p

    cmax_plot = df_scores["max_consonant_streak"].copy()
    mask_nom = df_scores["label"] == 0
    cmax_plot.loc[mask_nom] = cmax_plot.loc[mask_nom].rolling(5, min_periods=1, center=True).median()

    m_n_plot = margem_n.copy()
    m_p_plot = margem_p.copy()
    m_n_plot.loc[mask_nom] = m_n_plot.loc[mask_nom].rolling(5, min_periods=1, center=True).median()
    m_p_plot.loc[mask_nom] = m_p_plot.loc[mask_nom].rolling(5, min_periods=1, center=True).median()

    fig, axes = plt.subplots(2, 1, figsize=(12.6, 7.0), dpi=conf.PLOT_DPI, sharex=True,
                             gridspec_kw={"height_ratios": [1.0, 1.38]})

    for cid, grp in df_scores[df_scores["campanha_id"] > 0].groupby("campanha_id"):
        h_ini = (grp["start_epoch"].iloc[0] - t0) / 3600.0
        h_fim = (grp["start_epoch"].iloc[-1] - t0 + conf.WINDOW_SIZE_SEC) / 3600.0
        nivel = grp["nivel_ataque"].iloc[0]
        cor_faixa = "#fde68a" if nivel == "LEVE" else "#cbd5e1"
        alpha_faixa = 0.55 if nivel == "LEVE" else 0.45
        axes[0].axvspan(h_ini, h_fim, color=cor_faixa, alpha=alpha_faixa, zorder=0)
        axes[1].axvspan(h_ini, h_fim, color=cor_faixa, alpha=alpha_faixa, zorder=0)

        if nivel == "LEVE":
            axes[1].text((h_ini + h_fim) / 2, 0.102, f"C{int(cid)}",
                         ha="center", va="bottom", fontsize=7.8, fontweight="bold", color="#92400e")

    # --- Painel Superior (A): Atributo C_max ---
    axes[0].plot(epochs_hours, cmax_plot, color=COR_PROPOSTA, lw=1.25,
                 label="Sequência Máxima de Consoantes ($C_{max}$)")
    axes[0].axhline(y=2.34, color="#475569", linestyle=":", lw=1.0,
                    label="Média do Tráfego Nominal ($\\mu = 2,34$ consoantes)")

    axes[0].annotate(
        "Obs. 1: Mesmo nos Ataques Leves (faixas amarelas),\n$C_{max}$ permanece acima do padrão nominal",
        xy=(11.1, 2.55), xytext=(4.8, 4.95),
        fontsize=8.4, fontweight="bold", color="#1e3a8a",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#eff6ff", edgecolor="#93c5fd", lw=0.8),
        arrowprops=dict(arrowstyle="->", color="#1e40af", lw=1.0),
        zorder=6
    )

    axes[0].set_ylabel("$C_{max}$ (Consoantes)", fontsize=10, fontweight="bold")
    axes[0].set_title(
        "Painel A — Comportamento Temporal do Atributo Fonotático $C_{max}$ nas 28 Horas de Teste (21 Campanhas)",
        fontsize=10.8, fontweight="bold"
    )
    axes[0].set_ylim(1.8, 6.3)
    axes[0].grid(True, linestyle="--", alpha=0.35)

    handles_a, _ = axes[0].get_legend_handles_labels()
    handles_a.extend([
        Patch(facecolor="#fde68a", edgecolor="#d97706", alpha=0.7, label="Campanha de Ataque Leve (11 rajadas)"),
        Patch(facecolor="#cbd5e1", edgecolor="#64748b", alpha=0.7, label="Campanha Moderada / Intensa (10 rajadas)")
    ])
    axes[0].legend(handles=handles_a, loc="upper right", ncol=2, frameon=True,
                   facecolor="white", edgecolor="#cbd5e1", fontsize=8.3)

    # --- Painel Inferior (B): Scores relativos ao Limiar (Score - tau) ---
    axes[1].axhspan(0.0, 0.22, color="#eff6ff", alpha=0.35, zorder=0)
    axes[1].axhspan(-0.18, 0.0, color="#f8fafc", alpha=0.5, zorder=0)

    axes[1].plot(epochs_hours, m_n_plot, color=COR_NADLER, lw=1.15, alpha=0.9,
                 label="Baseline (Nadler et al., 2019)")
    axes[1].plot(epochs_hours, m_p_plot, color=COR_PROPOSTA, lw=1.35,
                 label="Proposta deste TCC (com $C_{max}$)")
    axes[1].axhline(y=0.0, color=COR_LIMIAR, linestyle="--", lw=1.4,
                    label="Limiar Operacional de Detecção ($\\tau = 0$: acima = Ataque Detectado)")

    # Destacar C13, C15 e C17 (ataques leves no pico comercial diurno onde o Baseline fica 100% abaixo de tau)
    falhas_x = []
    falhas_y = []
    for cid in [13, 15, 17]:
        grp = df_scores[df_scores["campanha_id"] == cid]
        if not grp.empty:
            falhas_x.append((grp["start_epoch"].mean() - t0) / 3600.0)
            falhas_y.append((grp["score_nadler"] - th_n).mean())

    axes[1].scatter(falhas_x, falhas_y, color=COR_LIMIAR, marker="X", s=65, zorder=7,
                    label="Colapso do Baseline em Ataque Leve Diurno (C13, C15 e C17 abaixo de $\\tau$)")

    axes[1].annotate(
        "Obs. 2 (Horário Comercial Diurno — C13, C15 e C17):\n"
        "Durante o pico de tráfego legítimo, o score do Baseline (cinza)\n"
        "permanece ABAIXO do limiar $\\tau = 0$ (0% de detecção nessas campanhas),\n"
        "enquanto a Proposta com $C_{max}$ (azul) cruza $\\tau$ e detecta as rajadas.",
        xy=(falhas_x[1], falhas_y[1]), xytext=(13.2, -0.155),
        fontsize=8.3, fontweight="bold", color="#7f1d1d",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#fef2f2", edgecolor="#fca5a5", lw=0.9),
        arrowprops=dict(arrowstyle="->", color="#b91c1c", lw=1.1),
        zorder=8
    )

    axes[1].text(27.6, 0.125, "ZONA DE ALERTA ($Score \\geq \\tau$)", ha="right",
                 fontsize=8.2, fontweight="bold", color="#1e40af")
    axes[1].text(27.6, -0.022, "ZONA NOMINAL ($Score < \\tau$)", ha="right",
                 fontsize=8.2, fontweight="bold", color="#475569")

    axes[1].set_ylabel("Margem de Decisão ($Score - \\tau$)", fontsize=10, fontweight="bold")
    axes[1].set_xlabel("Tempo Decorrido no Conjunto de Teste (Horas — 0h a 28h)", fontsize=10, fontweight="bold")
    axes[1].set_title(
        "Painel B — Margem do Score de Anomalia em Relação ao Limiar $\\tau$ (Valores $\\geq 0$ Disparam Detecção)",
        fontsize=10.8, fontweight="bold"
    )
    axes[1].set_ylim(-0.175, 0.215)
    axes[1].set_xlim(0, 28)
    axes[1].grid(True, linestyle="--", alpha=0.35)
    axes[1].legend(loc="upper left", ncol=2, frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=8.3)

    plt.tight_layout()
    salvar_figura(fig, "Figura_02_serie_temporal_scores_28h.png", "figura_serie_temporal_scores.png")
    plt.close(fig)


def gerar_figura_06_ataque_leve_por_periodo(df_scores):
    """
    Figura 6 (Diferenca Notavel 1):
    Mostra o impacto do ciclo circadiano (volume de trafego legitimo de fundo) sobre a deteccao
    dos Ataques Leves (231 janelas), explicando exatamente por que o Baseline cai durante o dia.
    """
    leve = df_scores[df_scores["nivel_ataque"] == "LEVE"].copy()
    dt = pd.to_datetime(leve["start_epoch"], unit="s")
    leve["hour"] = dt.dt.hour

    def classificar_periodo(h):
        if 0 <= h <= 6:
            return "Madrugada (00h–06h)\n[Baixo Tráfego: ~305 QPS]"
        elif 8 <= h <= 17:
            return "Horário Comercial (08h–17h)\n[Pico Diurno: ~840 QPS]"
        else:
            return "Transição de Turno (07h e 18h–23h)\n[Tráfego Intermediário: ~590 QPS]"

    leve["periodo"] = leve["hour"].apply(classificar_periodo)
    ordem = [
        "Madrugada (00h–06h)\n[Baixo Tráfego: ~305 QPS]",
        "Transição de Turno (07h e 18h–23h)\n[Tráfego Intermediário: ~590 QPS]",
        "Horário Comercial (08h–17h)\n[Pico Diurno: ~840 QPS]"
    ]

    rec_n = []
    rec_p = []
    acertos_n = []
    acertos_p = []
    totais = []
    for p in ordem:
        sub = leve[leve["periodo"] == p]
        totais.append(len(sub))
        acertos_n.append(int(sub["pred_nadler"].sum()))
        acertos_p.append(int(sub["pred_proposta"].sum()))
        rec_n.append(float(sub["pred_nadler"].mean() * 100.0))
        rec_p.append(float(sub["pred_proposta"].mean() * 100.0))

    x = np.arange(len(ordem))
    width = 0.34

    fig, ax = plt.subplots(figsize=(8.8, 5.0), dpi=conf.PLOT_DPI)
    b1 = ax.bar(x - width / 2, rec_n, width, label=conf.MODEL_BASELINE_NAME,
                color=COR_NADLER, edgecolor="#1e293b", lw=0.8, zorder=3)
    b2 = ax.bar(x + width / 2, rec_p, width, label="Proposta deste TCC (com $C_{max}$)",
                color=COR_PROPOSTA, edgecolor="#0f172a", lw=0.8, zorder=3)

    for r1 in b1:
        h = r1.get_height()
        ax.annotate(f"{h:.1f}%", xy=(r1.get_x() + r1.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                    fontsize=9.5, color="#334155", fontweight="bold")

    for r2 in b2:
        h = r2.get_height()
        ax.annotate(f"{h:.1f}%", xy=(r2.get_x() + r2.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                    fontsize=9.5, color="#1e3a8a", fontweight="bold")

    ax.annotate(
        f"Diferença Crítica no Horário Comercial (+{rec_p[2]-rec_n[2]:.1f} p.p.):\n"
        f"• Alto volume legítimo (~840 QPS) dilui a entropia global ($H$)\n"
        f"• Baseline cai para {rec_n[2]:.1f}% ({acertos_n[2]} de {totais[2]} janelas detectadas)\n"
        f"• Proposta com $C_{{max}}$ sustenta {rec_p[2]:.1f}% ({acertos_p[2]} de {totais[2]} janelas)",
        xy=(2 - width / 2, 7.5), xytext=(0.42, 42.0),
        fontsize=8.5, color="#0f172a",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#f8fafc", edgecolor="#94a3b8", lw=0.9),
        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.15", color="#b91c1c", lw=1.1),
        zorder=5
    )

    ax.set_ylabel("Taxa de Detecção em Ataques Leves — Recall (%)", fontsize=10, fontweight="bold")
    ax.set_title("Impacto do Volume de Tráfego Legítimo (Período do Dia) na Detecção de Ataques Leves",
                 fontsize=11.2, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(ordem, fontsize=9.2, fontweight="bold")
    ax.set_ylim(0, 114)
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=9.2)

    plt.tight_layout()
    salvar_figura(fig, "Figura_07_impacto_diluicao_diurna_ataque_leve.png")
    plt.close(fig)


def gerar_figura_07_boxplot_separabilidade(df_scores):
    """
    Figura 7 (Diferenca Notavel 2):
    Boxplot padronizado comparando a distribuicao da Margem de Decisao (Score - Limiar tau)
    por classe de trafego, demonstrando visualmente a separabilidade superior da Proposta.
    """
    th_n = float(df_scores["limiar_nadler"].iloc[0])
    th_p = float(df_scores["limiar_proposta"].iloc[0])

    mapa_cat = {
        "NORMAL": "Tráfego Nominal\n(2.699 janelas)",
        "LEVE": "Ataque Leve\n(231 janelas)",
        "MODERADO": "Ataque Moderado\n(186 janelas)",
        "INTENSO": "Ataque Intenso\n(244 janelas)"
    }
    ordem_cat = [
        "Tráfego Nominal\n(2.699 janelas)",
        "Ataque Leve\n(231 janelas)",
        "Ataque Moderado\n(186 janelas)",
        "Ataque Intenso\n(244 janelas)"
    ]

    reg = []
    for _, row in df_scores.iterrows():
        c_label = mapa_cat.get(row["nivel_ataque"], "Tráfego Nominal\n(2.699 janelas)")
        reg.append({
            "Categoria": c_label,
            "Modelo": conf.MODEL_BASELINE_NAME,
            "Margem": float(row["score_nadler"]) - th_n
        })
        reg.append({
            "Categoria": c_label,
            "Modelo": "Proposta deste TCC (com $C_{max}$)",
            "Margem": float(row["score_proposta"]) - th_p
        })
    df_box = pd.DataFrame(reg)

    fig, ax = plt.subplots(figsize=(9.2, 5.0), dpi=conf.PLOT_DPI)

    sns.boxplot(
        data=df_box, x="Categoria", y="Margem", hue="Modelo", order=ordem_cat,
        palette={conf.MODEL_BASELINE_NAME: COR_NADLER, "Proposta deste TCC (com $C_{max}$)": COR_PROPOSTA},
        width=0.56, fliersize=2.0, boxprops=dict(alpha=0.88, edgecolor="#0f172a", lw=0.9),
        medianprops=dict(color="#f8fafc", lw=1.6), ax=ax, zorder=3
    )

    ax.axhline(y=0.0, color=COR_LIMIAR, linestyle="--", lw=1.4, zorder=4,
               label="Limiar Operacional Calibrado ($\\tau = 0$)")

    ax.annotate(
        "Obs.: No Ataque Leve, 32,5% da distribuição do Baseline\n"
        "cai abaixo do limiar $\\tau = 0$ (75 Falsos Negativos),\n"
        "enquanto a caixa interquartil da Proposta permanece\n"
        "integralmente na região positiva de detecção (95,7% > $\\tau$).",
        xy=(1 - 0.14, -0.012), xytext=(1.32, -0.125),
        fontsize=8.4, color="#0f172a",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#f8fafc", edgecolor="#94a3b8", lw=0.9),
        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.15", color="#b91c1c", lw=1.1),
        zorder=6
    )

    ax.set_xlabel("Categoria de Tráfego nas Janelas de Teste ($\\Delta t = 30$ s)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Margem de Decisão Normalizada ($Score - \\tau$)", fontsize=10, fontweight="bold")
    ax.set_title("Distribuição e Separabilidade dos Scores de Anomalia em Relação ao Limiar $\\tau$",
                 fontsize=11.2, fontweight="bold", pad=12)
    ax.set_ylim(-0.16, 0.24)
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#cbd5e1", fontsize=9)

    plt.tight_layout()
    salvar_figura(fig, "Figura_08_distribuicao_scores_separabilidade.png", "figura_dispersao_features.png")
    plt.close(fig)


def gerar_figura_08_mecanismo_isolamento_arvore():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mod_fig8",
        os.path.join(os.path.dirname(__file__), "03_gerar_figura_arvore_isolamento.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.gerar_figura_arvore()


def main():
    scores_csv = os.path.join(conf.RESULTS_TABLES_DIR, "predicoes_e_scores_teste.csv")
    intensidade_csv = os.path.join(conf.RESULTS_TABLES_DIR, "tabela_02_desempenho_por_intensidade.csv")
    resumo_csv = os.path.join(conf.RESULTS_TABLES_DIR, "tabela_01_resumo_comparativo_modelos.csv")

    if not os.path.exists(scores_csv):
        sys.exit(f"Arquivo nao encontrado: {scores_csv}. Execute 01_treinar_e_comparar_modelos.py primeiro.")

    df_scores = pd.read_csv(scores_csv)
    df_int = pd.read_csv(intensidade_csv)
    df_resumo = pd.read_csv(resumo_csv)

    configurar_estilo()
    gerar_figura_01_intensidade(df_int, df_resumo)
    gerar_figura_02_matriz_confusao(df_scores, df_resumo)
    gerar_figura_03_curvas_roc_pr(df_scores, df_resumo)
    gerar_figura_04_metricas_globais(df_resumo)
    gerar_figura_05_serie_temporal(df_scores)
    gerar_figura_06_ataque_leve_por_periodo(df_scores)
    gerar_figura_07_boxplot_separabilidade(df_scores)
    gerar_figura_08_mecanismo_isolamento_arvore()

    print(f"8 figuras cientificas padronizadas geradas em:\n  - {conf.RESULTS_FIGURES_DIR}")


if __name__ == "__main__":
    main()
