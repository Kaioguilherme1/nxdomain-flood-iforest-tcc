# Registro Metodológico: Avaliação Experimental por Intensidade de Ataque (Leve, Moderado e Intenso)

**Projeto:** Detecção de Anomalias em Logs DNS utilizando Aprendizado de Máquina  
**Instituição:** Universidade Federal de Roraima (UFRR) - Departamento de Ciência da Computação (DCC)  
**Autor:** Kaio Guilherme Ferraz de Sousa Silva  
**Orientador:** Prof. Dr. Felipe Lobo  
**Data:** Novembro de 2026  

---

## 1. Parametrização Real do `dnsperf` nas 21 Campanhas de Ataque

As 21 campanhas controladas de *NXDOMAIN Flood* foram geradas na bancada experimental (`campanha-nxdomain.py`) com os seguintes parâmetros da ferramenta `dnsperf`:
1. **Ataque Leve (11 campanhas, 231 janelas de 30s):**
   `dnsperf -s 192.168.2.200 -d domains.txt -l 600 -c 10 -Q 1000 -t 2`
2. **Ataque Moderado (6 campanhas, 186 janelas de 30s):**
   `dnsperf -s 192.168.2.200 -d domains.txt -l 900 -c 40 -Q 5000 -t 2`
3. **Ataque Intenso (4 campanhas, 244 janelas de 30s):**
   `dnsperf -s 192.168.2.200 -d domains.txt -l 1800 -c 100 -Q 20000 -t 2`

---

## 2. Tabela Oficial de Resultados Experimentais (`dataset_features_48h_w30s.csv`)

| Escopo / Regime | Modelo Avaliado | Acurácia (%) | Precisão (%) | Recall / Sensibilidade (%) | FAR / Falso Alarme (%) | F1-Score (%) | ROC-AUC | PR-AUC | TP | FP | TN | FN |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Global (3.360 janelas)** | Baseline (Nadler et al., 2019) | 96.99 | 95.75 | 88.65 | 0.96 | 92.07 | 0.9922 | 0.9750 | 586 | 26 | 2673 | **75** |
| **Global (3.360 janelas)** | **Proposta deste TCC (com $C_{\text{max}}$)** | **98.96** | **96.30** | **98.49** | **0.93** | **97.38** | **0.9995** | **0.9980** | **651** | **25** | **2674** | **10** |
| **Ataque Leve — Geral (231 janelas)** | Baseline vs. Proposta | — | — | **67.53% → 95.67%** (+28.14 p.p.) | — | — | — | — | 156 → 221 | — | — | 75 → 10 |
| **Ataque Leve — Horário Comercial (08h–17h, 63 janelas)** | Baseline vs. Proposta | — | — | **0.00% → 84.13%** (+84.13 p.p.) | — | — | — | — | 0 → 53 | — | — | 63 → 10 |
| **Ataque Moderado (186 janelas)** | Baseline vs. Proposta | — | — | **100.00% → 100.00%** | — | — | — | — | 186 → 186 | — | — | 0 → 0 |
| **Ataque Intenso (244 janelas)** | Baseline vs. Proposta | — | — | **100.00% → 100.00%** | — | — | — | — | 244 → 244 | — | — | 0 → 0 |
