# Guia de Resultados, Figuras e Tabelas do TCC

Esta pasta centraliza os artefatos experimentais da comparação entre o **Baseline (Nadler et al., 2019 — 4 atributos)** e a **Proposta deste TCC (5 atributos com $C_{\max}$)**.

---

## 1. Artefatos Exatos do Texto Final do TCC (`03_Artefatos_Finais_TCC/`)

Gerados automaticamente em ~5 segundos com `python3 05_Codigo_e_Scripts/run_pipeline_completo.py --tcc`:

1. **`Figura_1_mecanismo_isolamento.png`**: Mecanismo de isolamento na *iTree* e distribuição empírica da profundidade de corte.
2. **`Figura_2_matrizes_confusao.png`**: Matrizes de confusão comparativas nas `3.360` janelas de teste (`FN = 75` no *Baseline* vs. `FN = 10` na Proposta).
3. **`Figura_3_recall_por_intensidade.png`**: *Recall* estratificado por nível de intensidade (Leve `67,5%` → `95,7%`; Moderado e Intenso `100,0%`).
4. **`Figura_4_diluicao_diurna_ataque_leve.png`**: Impacto da diluição diurna nos ataques leves (`0,0%` vs. `84,1%` no horário comercial 08h–17h).
5. **`Tabela_3_campanhas_ataque.csv`**: Parametrização das 21 campanhas e carga efetiva integrada (`2.306.778` consultas em `661` janelas).
6. **`Tabela_4_desempenho_global.csv`**: Métricas globais consolidadas (Acurácia, Precisão, Recall, F1, FAR, FP, FN, AUC-ROC e AUC-PR).
7. **`Tabela_5_atributos_por_intensidade.csv`**: Médias e desvios percentuais ($\Delta\%$) dos cinco atributos por classe/intensidade.

---

## 2. Suíte Estendida de Figuras (`01_Figuras_TCC/`, 300 DPI)

Geradas pelo comando `python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 4`:

1. `Figura_01_mecanismo_isolamento_itree.png` — Mecanismo de isolamento e histograma real de profundidade nas 100 *iTrees*.
2. `Figura_02_serie_temporal_scores_28h.png` — Série temporal de $C_{\max}$ e margem de decisão ($\text{Score} - \tau$) ao longo das 28h de teste.
3. `Figura_03_matrizes_confusao.png` — Matrizes de confusão detalhadas (contagens absolutas e percentuais).
4. `Figura_04_metricas_globais_comparativo.png` — Comparativo visual de Acurácia, Precisão, Recall e F1-Score.
5. `Figura_05_curvas_roc_e_precision_recall.png` — Curvas ROC (`0,9995` vs. `0,9922`) e Precision-Recall (`0,9980` vs. `0,9750`).
6. `Figura_06_recall_por_intensidade_ataque.png` — Recall por intensidade com anotações dos ganhos.
7. `Figura_07_impacto_diluicao_diurna_ataque_leve.png` — Quebra por período do dia (Madrugada, Transição e Horário Comercial).
8. `Figura_08_distribuicao_scores_separabilidade.png` — Boxplot da margem de decisão ($\text{Score} - \tau$) por classe de tráfego.

---

## 3. Tabelas e Métricas Completas (`02_Tabelas_e_Metricas/`)

* `tabela_01_resumo_comparativo_modelos.csv`: Métricas globais consolidadas.
* `tabela_02_desempenho_por_intensidade.csv`: Comparação estratificada por nível de campanha (`LEVE`, `MODERADO`, `INTENSO`).
* `tabela_03_desempenho_por_campanha_21.csv`: Desempenho individual em cada uma das 21 campanhas.
* `tabela_04_ataque_leve_por_periodo_dia.csv`: Estratificação dos ataques leves por faixa horária.
* `predicoes_e_scores_teste.csv`: Série completa das `3.360` janelas de teste com atributos, escores e predições.
