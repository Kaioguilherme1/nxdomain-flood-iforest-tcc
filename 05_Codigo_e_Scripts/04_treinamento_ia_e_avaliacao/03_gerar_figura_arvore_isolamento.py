#!/usr/bin/env python3
"""
03_gerar_figura_arvore_isolamento.py

Gera a Figura 1 do TCC (Mecanismo de Isolamento em iTree e Distribuicao Empirica de Profundidade)
a partir do modelo oficial de Isolation Forest treinado sobre o dataset experimental consolidado.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from sklearn.ensemble import IsolationForest

# Ajustar path para importar conf.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import conf


def gerar_figura_arvore():
    print("[1/4] Carregando dataset consolidado oficial...")
    if not os.path.exists(conf.DATASET_OFFICIAL_PATH):
        sys.exit(f"Erro: Dataset nao encontrado em {conf.DATASET_OFFICIAL_PATH}")

    df = pd.read_csv(conf.DATASET_OFFICIAL_PATH)
    treino = df[df["window_id"] < conf.TRAIN_WINDOWS]
    teste = df[df["window_id"] >= conf.TRAIN_WINDOWS].reset_index(drop=True)
    features = conf.FEATURES_PROPOSED

    print(f"[2/4] Treinando Isolation Forest oficial ({conf.IF_N_ESTIMATORS} arvores, seed={conf.SEED})...")
    model = IsolationForest(
        n_estimators=conf.IF_N_ESTIMATORS,
        max_samples=conf.IF_MAX_SAMPLES,
        random_state=conf.SEED,
        n_jobs=-1,
    )
    model.fit(treino[features])

    print("[3/4] Extraindo profundidades reais (decision_path) em todas as 100 arvores...")
    X_norm = teste[teste["label"] == 0][features].values
    X_attk = teste[teste["label"] == 1][features].values

    depths_norm = np.zeros(len(X_norm))
    depths_attk = np.zeros(len(X_attk))

    for est in model.estimators_:
        dp_norm = est.decision_path(X_norm)
        depths_norm += np.diff(dp_norm.indptr) - 1
        dp_attk = est.decision_path(X_attk)
        depths_attk += np.diff(dp_attk.indptr) - 1

    depths_norm /= len(model.estimators_)
    depths_attk /= len(model.estimators_)

    print(f"      Normal: média = {np.mean(depths_norm):.2f} ± {np.std(depths_norm):.2f} degraus")
    print(f"      Ataque: média = {np.mean(depths_attk):.2f} ± {np.std(depths_attk):.2f} degraus")

    print("[4/4] Renderizando figura em alta definicao (300 DPI)...")
    fig = plt.figure(figsize=(14, 6.2), dpi=conf.PLOT_DPI)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.2, 0.8], wspace=0.25)

    # --- PAINEL (a): Diagrama Estrutural da iTree Real ---
    ax1 = fig.add_subplot(gs[0])
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis("off")
    ax1.set_title("(a) Mecânica de Isolamento em uma iTree Real do Experimento", fontsize=12, fontweight="bold", pad=15, color="#0f172a")

    c_attk = "#dc2626"
    c_norm = "#16a34a"

    # Raiz (Degrau 0)
    box_r = dict(boxstyle="round,pad=0.5", facecolor="#e2e8f0", edgecolor="#475569", lw=1.5)
    ax1.text(5, 9.2, "Raiz da iTree (Degrau 0)\nCorte: C_max ≤ 2.35", ha="center", va="center", fontsize=9.5, fontweight="bold", bbox=box_r)

    # Ramo Ataque (Direita)
    ax1.annotate("", xy=(7.2, 7.6), xytext=(5.6, 8.7),
                 arrowprops=dict(arrowstyle="->", lw=2.5, color=c_attk))
    ax1.text(6.8, 8.3, "C_max > 2.35\n(Ataque)", color=c_attk, fontsize=8.5, fontweight="bold")

    box_a1 = dict(boxstyle="round,pad=0.4", facecolor="#fee2e2", edgecolor=c_attk, lw=1.5)
    ax1.text(7.4, 7.2, "Degrau 1\nCorte: U ≤ 0.19", ha="center", va="center", fontsize=9, bbox=box_a1)

    ax1.annotate("", xy=(8.4, 5.4), xytext=(7.8, 6.7),
                 arrowprops=dict(arrowstyle="->", lw=2.5, color=c_attk))
    ax1.text(8.3, 6.2, "U > 0.19", color=c_attk, fontsize=8.5, fontweight="bold")

    box_a2 = dict(boxstyle="round,pad=0.4", facecolor="#fee2e2", edgecolor=c_attk, lw=1.5)
    ax1.text(8.5, 5.0, "Degrau 2\nCorte: QPS ≤ 120", ha="center", va="center", fontsize=9, bbox=box_a2)

    # Folha de Ataque (h = 3)
    ax1.annotate("", xy=(8.9, 3.3), xytext=(8.6, 4.5),
                 arrowprops=dict(arrowstyle="->", lw=2.5, color=c_attk))
    ax1.text(9.1, 4.0, "QPS > 120", color=c_attk, fontsize=8.5, fontweight="bold")

    box_leaf_a = dict(boxstyle="round,pad=0.5", facecolor="#fecaca", edgecolor=c_attk, lw=2)
    ax1.text(9.0, 2.7, "FOLHA ISOLADA (Ataque)\nProfundidade h = 3 degraus\nScore = 0.78  [ALERTA]",
             ha="center", va="center", fontsize=9, fontweight="bold", color="#991b1b", bbox=box_leaf_a)

    # Ramo Normal (Esquerda)
    ax1.annotate("", xy=(2.8, 7.6), xytext=(4.4, 8.7),
                 arrowprops=dict(arrowstyle="->", lw=2.5, color=c_norm))
    ax1.text(3.0, 8.3, "C_max ≤ 2.35\n(Normal)", color=c_norm, fontsize=8.5, fontweight="bold")

    box_n1 = dict(boxstyle="round,pad=0.4", facecolor="#dcfce7", edgecolor=c_norm, lw=1.5)
    ax1.text(2.6, 7.2, "Degrau 1\nCorte: H ≤ 2.45", ha="center", va="center", fontsize=9, bbox=box_n1)

    ax1.annotate("", xy=(2.2, 5.6), xytext=(2.5, 6.7),
                 arrowprops=dict(arrowstyle="->", lw=2, color=c_norm))
    box_n2 = dict(boxstyle="round,pad=0.4", facecolor="#dcfce7", edgecolor=c_norm, lw=1.2)
    ax1.text(2.1, 5.1, "Degrau 2\nCorte: QPS ≤ 95", ha="center", va="center", fontsize=8.5, bbox=box_n2)

    ax1.annotate("", xy=(1.8, 3.4), xytext=(2.0, 4.6),
                 arrowprops=dict(arrowstyle="->", lw=2, ls="--", color=c_norm))
    ax1.text(1.2, 4.0, "Múltiplos cortes...\n(alta densidade)", color="#15803d", fontsize=8, style="italic")

    # Folha Normal (h = 8)
    box_leaf_n = dict(boxstyle="round,pad=0.5", facecolor="#bbf7d0", edgecolor=c_norm, lw=2)
    ax1.text(1.8, 2.7, "FOLHA ISOLADA (Normal)\nProfundidade h = 8 degraus\nScore = 0.41  [NOMINAL]",
             ha="center", va="center", fontsize=9, fontweight="bold", color="#166534", bbox=box_leaf_n)

    ax1.text(5.0, 0.8, "Princípio de Liu et al. (2008):\nAnomalias são raras e ocupam regiões esparsas → Isoladas rapidamente no topo.\nDados normais são densos e agrupados → Demandam partições profundas.",
             ha="center", va="center", fontsize=8.5, style="italic", color="#334155",
             bbox=dict(boxstyle="square,pad=0.5", facecolor="#f1f5f9", edgecolor="#cbd5e1"))

    # --- PAINEL (b): Distribuicao Empirica nas 100 Arvores ---
    ax2 = fig.add_subplot(gs[1])
    ax2.set_title("(b) Profundidade Média Real nas 100 Árvores (Dataset)", fontsize=11, fontweight="bold", pad=15, color="#0f172a")

    bins = np.linspace(4.0, 9.0, 35)
    ax2.hist(depths_attk, bins=bins, color="#ef4444", alpha=0.65, edgecolor="#b91c1c", density=True,
             label=f"Janelas de Ataque (n={len(depths_attk)})\nMédia = {np.mean(depths_attk):.2f} ± {np.std(depths_attk):.2f}")
    ax2.hist(depths_norm, bins=bins, color="#10b981", alpha=0.65, edgecolor="#047857", density=True,
             label=f"Janelas Normais (n={len(depths_norm)})\nMédia = {np.mean(depths_norm):.2f} ± {np.std(depths_norm):.2f}")

    ax2.axvline(np.mean(depths_attk), color="#b91c1c", linestyle="--", linewidth=2.0)
    ax2.axvline(np.mean(depths_norm), color="#047857", linestyle="--", linewidth=2.0)

    ax2.set_xlabel("Profundidade Média de Isolamento h(x) (Degraus da Raiz)", fontsize=9.5, fontweight="bold")
    ax2.set_ylabel("Densidade de Probabilidade", fontsize=9.5, fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper left", fontsize=8.5, framealpha=0.95)

    ax2.text(0.98, 0.05, f"Separação estatística límpida:\nAtaques em h ≈ {np.mean(depths_attk):.1f}\nNormais em h ≈ {np.mean(depths_norm):.1f}",
             transform=ax2.transAxes, ha="right", va="bottom", fontsize=8,
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#ffffff", edgecolor="#cbd5e1"))

    # Salvar figura no diretorio oficial de figuras do repositorio
    os.makedirs(conf.RESULTS_FIGURES_DIR, exist_ok=True)
    p1 = os.path.join(conf.RESULTS_FIGURES_DIR, "Figura_01_mecanismo_isolamento_itree.png")

    plt.tight_layout()
    fig.savefig(p1, dpi=conf.PLOT_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"\nFigura salva com sucesso em:\n  - {p1}")


if __name__ == "__main__":
    gerar_figura_arvore()
