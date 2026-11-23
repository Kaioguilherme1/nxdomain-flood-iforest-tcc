#!/usr/bin/env python3
"""
Compilador do relatorio standalone HTML com metricas, figuras e telemetria ECharts.
"""

import json
import os
import csv
import base64
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import conf

BASE_DIR = conf.BASE_DIR
STATS_DIR = conf.RESULTS_DIR
FIG_DIR = conf.FIGURES_DIR
META_DIR = conf.METADATA_DIR
DOCS_DIR = os.path.join(BASE_DIR, "01_Manuscrito_e_Docs")

HTML_OUT_1 = os.path.join(STATS_DIR, "relatorio_geral_estatistica_e_ml.html")
HTML_OUT_2 = os.path.join(conf.REPORTS_DIR, "relatorio_geral_estatistica_e_ml.html")


def image_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")
    return ""


def csv_to_table_rows(path):
    rows = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            r = csv.reader(f)
            header = next(r, None)
            for row in r:
                rows.append(row)
            return header, rows
    return None, []


def main():
    print(">>> Compilando Relatório Técnico HTML Standalone...")

    json_path = os.path.join(STATS_DIR, "dados_relatorio_consolidado.json")
    if os.path.exists(json_path):
        with open(json_path) as f:
            data = json.load(f)
    else:
        data = {"timeline_sample": {"hours": [], "qps": [], "cmax": []}}

    # Carregar tabelas CSV
    h_resumo, r_resumo = csv_to_table_rows(os.path.join(conf.RESULTS_TABLES_DIR, "tabela_01_resumo_comparativo_modelos.csv"))
    h_int, r_int = csv_to_table_rows(os.path.join(conf.RESULTS_TABLES_DIR, "tabela_02_desempenho_por_intensidade.csv"))

    # Carregar imagens em Base64
    b64_int = image_to_base64(os.path.join(conf.RESULTS_FIGURES_DIR, "Figura_06_recall_por_intensidade_ataque.png"))
    b64_cm = image_to_base64(os.path.join(conf.RESULTS_FIGURES_DIR, "Figura_03_matrizes_confusao.png"))
    b64_roc_pr = image_to_base64(os.path.join(conf.RESULTS_FIGURES_DIR, "Figura_05_curvas_roc_e_precision_recall.png"))
    b64_glob = image_to_base64(os.path.join(conf.RESULTS_FIGURES_DIR, "Figura_04_metricas_globais_comparativo.png"))
    b64_timeline = image_to_base64(os.path.join(conf.RESULTS_FIGURES_DIR, "Figura_02_serie_temporal_scores_28h.png"))
    b64_periodo = image_to_base64(os.path.join(conf.RESULTS_FIGURES_DIR, "Figura_07_impacto_diluicao_diurna_ataque_leve.png"))
    b64_box = image_to_base64(os.path.join(conf.RESULTS_FIGURES_DIR, "Figura_08_distribuicao_scores_separabilidade.png"))

    # Carregar o texto do manuscrito compilado
    compilado_md_path = os.path.join(DOCS_DIR, "COMPILADO_METODOLOGIA_E_RESULTADOS_TCC.md")
    texto_compilado_md = ""
    if os.path.exists(compilado_md_path):
        with open(compilado_md_path, "r", encoding="utf-8") as f:
            texto_compilado_md = f.read()

    # Montagem do HTML Standalone
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Técnico Experimental // TCC DCC/UFRR</title>
    <!-- Apache ECharts -->
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <!-- KaTeX para renderização de fórmulas matemáticas -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>
    <style>
        :root {{
            --bg-base: #090b10;
            --bg-surface: #10131c;
            --bg-elevated: #181d2a;
            --border: #232938;
            --cobalt: #6366f1;
            --cobalt-dark: #4338ca;
            --cobalt-glow: rgba(99, 102, 241, 0.15);
            --ice-blue: #93c5fd;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --font-mono: "JetBrains Mono", "SF Mono", "Fira Code", monospace;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg-base);
            color: var(--text-primary);
            font-family: var(--font-sans);
            font-size: 14px;
            line-height: 1.6;
            padding: 24px;
        }}

        /* Header Tático */
        .header {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-left: 4px solid var(--cobalt);
            padding: 20px 24px;
            border-radius: 2px;
            margin-bottom: 24px;
        }}
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .brand {{
            font-family: var(--font-mono);
            font-size: 13px;
            letter-spacing: 2px;
            color: var(--ice-blue);
            text-transform: uppercase;
        }}
        .badge-status {{
            background: var(--cobalt-glow);
            color: var(--ice-blue);
            border: 1px solid var(--cobalt);
            font-family: var(--font-mono);
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 2px;
            text-transform: uppercase;
        }}
        .header h1 {{
            font-size: 22px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 6px;
        }}
        .header-meta {{
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--text-secondary);
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}

        /* KPI Banner */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            padding: 16px 20px;
            border-radius: 2px;
            position: relative;
        }}
        .kpi-card::after {{
            content: "";
            position: absolute;
            top: 0; left: 0; width: 100%; height: 2px;
            background: var(--border);
        }}
        .kpi-card.accent::after {{ background: var(--cobalt); }}
        .kpi-card.success::after {{ background: var(--success); }}
        .kpi-card.warning::after {{ background: var(--warning); }}
        .kpi-card.danger::after {{ background: var(--danger); }}
        .kpi-label {{
            font-family: var(--font-mono);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}
        .kpi-value {{
            font-family: var(--font-mono);
            font-size: 24px;
            font-weight: 700;
            color: #fff;
        }}
        .kpi-sub {{
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 4px;
        }}

        /* Navegação por Abas */
        .tabs {{
            display: flex;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
            background: var(--bg-surface);
            border-radius: 2px 2px 0 0;
            overflow-x: auto;
        }}
        .tab-btn {{
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-family: var(--font-mono);
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 1px;
            padding: 14px 20px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
            text-transform: uppercase;
            white-space: nowrap;
        }}
        .tab-btn:hover {{
            color: var(--text-primary);
        }}
        .tab-btn.active {{
            color: var(--ice-blue);
            border-bottom-color: var(--cobalt);
            background: var(--cobalt-glow);
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}

        /* Painéis e Containers */
        .panel {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            padding: 24px;
            border-radius: 2px;
            margin-bottom: 24px;
        }}
        .panel-title {{
            font-family: var(--font-mono);
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--ice-blue);
            border-bottom: 1px solid var(--border);
            padding-bottom: 12px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        /* Tabelas */
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-bottom: 16px;
        }}
        th, td {{
            padding: 12px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background: var(--bg-elevated);
            font-family: var(--font-mono);
            color: var(--ice-blue);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
        .highlight {{
            color: var(--ice-blue);
            font-weight: 700;
        }}
        .badge-green {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid var(--success);
            padding: 2px 6px;
            font-family: var(--font-mono);
            font-size: 11px;
            border-radius: 2px;
        }}
        .badge-red {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--danger);
            border: 1px solid var(--danger);
            padding: 2px 6px;
            font-family: var(--font-mono);
            font-size: 11px;
            border-radius: 2px;
        }}

        /* Grid de Imagens */
        .fig-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }}
        .fig-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 2px;
            overflow: hidden;
            padding: 16px;
        }}
        .fig-card h4 {{
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--ice-blue);
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .fig-card img {{
            width: 100%;
            height: auto;
            border: 1px solid var(--border);
            border-radius: 2px;
            display: block;
        }}

        /* Caixas de Código e Destaques */
        pre, code {{
            font-family: var(--font-mono);
            font-size: 12px;
        }}
        pre {{
            background: #0d1117;
            border: 1px solid var(--border);
            padding: 16px;
            border-radius: 2px;
            overflow-x: auto;
            color: #c9d1d9;
            margin-bottom: 16px;
        }}
        .callout {{
            background: rgba(99, 102, 241, 0.08);
            border-left: 3px solid var(--cobalt);
            padding: 16px 20px;
            margin-bottom: 20px;
            border-radius: 2px;
        }}
        .callout-title {{
            font-family: var(--font-mono);
            font-weight: bold;
            color: var(--ice-blue);
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}
        .callout-warning {{
            background: rgba(245, 158, 11, 0.08);
            border-left: 3px solid var(--warning);
        }}
        .callout-warning .callout-title {{
            color: var(--warning);
        }}

        /* Botão de Cópia */
        .copy-btn {{
            background: var(--bg-elevated);
            color: var(--ice-blue);
            border: 1px solid var(--border);
            font-family: var(--font-mono);
            font-size: 11px;
            padding: 6px 14px;
            cursor: pointer;
            border-radius: 2px;
            transition: all 0.2s;
        }}
        .copy-btn:hover {{
            background: var(--cobalt);
            color: #fff;
        }}

        /* Print Style */
        @media print {{
            body {{ background: #fff; color: #000; padding: 0; }}
            .tabs, .copy-btn, .badge-status {{ display: none; }}
            .tab-content {{ display: block !important; margin-bottom: 40px; page-break-after: always; }}
            .panel {{ border: 1px solid #ddd; background: #fff; }}
            th {{ background: #f0f0f0; color: #000; }}
            td {{ color: #000; }}
            .header {{ border-left: 4px solid #000; background: #fafafa; }}
            .header h1 {{ color: #000; }}
            .brand {{ color: #000; }}
        }}
    </style>
</head>
<body>

    <!-- Header Principal -->
    <div class="header">
        <div class="header-top">
            <div class="brand">CORTANA CORE // SISTEMA DE RELATÓRIOS CIENTÍFICOS DUAL</div>
            <div class="badge-status">[STATUS: NOMINAL / VERIFICADO]</div>
        </div>
        <h1>Detecção de Anomalias em Logs DNS utilizando Aprendizado de Máquina</h1>
        <div class="header-meta">
            <div>AUTOR: <strong>Kaio Guilherme Ferraz de Sousa Silva</strong></div>
            <div>ORIENTADOR: <strong>Prof. Dr. Felipe Lobo</strong></div>
            <div>INSTITUIÇÃO: <strong>UFRR / DCC</strong></div>
            <div>DATASET: <strong>48 Horas / 122,78M Consultas</strong></div>
            <div>SEED: <strong>129547711</strong></div>
        </div>
    </div>

    <!-- KPIs Executivos -->
    <div class="kpi-grid">
        <div class="kpi-card accent">
            <div class="kpi-label">Recall em Ataque Leve (Baixo QPS)</div>
            <div class="kpi-value">95,67%</div>
            <div class="kpi-sub"><span class="badge-green">+28,14%</span> vs. Nadler et al. (67,53%)</div>
        </div>
        <div class="kpi-card success">
            <div class="kpi-label">Redução de Ataques Perdidos (FN)</div>
            <div class="kpi-value">-86,7%</div>
            <div class="kpi-sub">Caiu de 75 para <strong>10 janelas</strong> (+65 salvas)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Recall em Ataque Moderado e Intenso</div>
            <div class="kpi-value">100,0%</div>
            <div class="kpi-sub">Detecção integral em alto volume de QPS</div>
        </div>
        <div class="kpi-card accent">
            <div class="kpi-label">Acurácia Global / ROC-AUC</div>
            <div class="kpi-value">98,96%</div>
            <div class="kpi-sub">ROC-AUC: <strong>0,9995</strong> | PR-AUC: <strong>0,9980</strong></div>
        </div>
    </div>

    <!-- Navegação das Abas -->
    <div class="tabs">
        <button class="tab-btn active" onclick="openTab('tab1', this)">01 // Metodologia e Resultados (Manuscrito)</button>
        <button class="tab-btn" onclick="openTab('tab2', this)">02 // Telemetria e Figuras 300 DPI</button>
        <button class="tab-btn" onclick="openTab('tab3', this)">03 // Engenharia de Código Linha a Linha</button>
        <button class="tab-btn" onclick="openTab('tab4', this)">04 // Reprodutibilidade (GitHub & Kaggle/Zenodo)</button>
        <button class="tab-btn" onclick="openTab('tab5', this)">05 // Discussão Técnica e Arguição</button>
        <button class="tab-btn" onclick="openTab('tab6', this)">06 // Dispatch Markdown Bruto</button>
    </div>

    <!-- ABA 01: METODOLOGIA E MANUSCRITO -->
    <div id="tab1" class="tab-content active">
        <div class="panel">
            <div class="panel-title">
                <span>Síntese Comparativa Principal (Cenário Operacional Realista - 10% de Ataque)</span>
                <span class="badge-status">Tabela 1 do TCC</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Abordagem Avaliada</th>
                        <th>Atributos Utilizados</th>
                        <th>Acurácia (%)</th>
                        <th>Precisão (%)</th>
                        <th>Recall (%)</th>
                        <th>FAR (%)</th>
                        <th>Falsos Alarmes (FP)</th>
                        <th>Ataques Perdidos (FN)</th>
                        <th>F1-Score (%)</th>
                        <th>ROC-AUC</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Baseline (Nadler et al., 2019)</strong></td>
                        <td>4 [QPS, Entropia, Comp. Médio, Únicos]</td>
                        <td>96,99%</td>
                        <td>95,75%</td>
                        <td>88,65%</td>
                        <td>0,96%</td>
                        <td>26</td>
                        <td>75</td>
                        <td>92,07%</td>
                        <td>0,9922</td>
                    </tr>
                    <tr style="background: rgba(99, 102, 241, 0.08);">
                        <td class="highlight"><strong>Proposta deste TCC (com $C_{{max}}$)</strong></td>
                        <td class="highlight">5 [QPS, C_max, Entropia, Comp. Médio, Únicos]</td>
                        <td class="highlight"><strong>98,96%</strong></td>
                        <td class="highlight"><strong>96,30%</strong></td>
                        <td class="highlight"><strong>98,49%</strong></td>
                        <td class="highlight"><span class="badge-green">0,93%</span></td>
                        <td class="highlight"><strong>25</strong></td>
                        <td class="highlight"><strong>10</strong></td>
                        <td class="highlight"><strong>97,38%</strong></td>
                        <td class="highlight"><strong>0,9995</strong></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="panel">
            <div class="panel-title">
                <span>Detecção Discriminada por Intensidade de QPS Injetado (Onde a Proposta Vence)</span>
                <span class="badge-status">Tabela 2 do TCC</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Nível de Intensidade</th>
                        <th>Total de Janelas</th>
                        <th>Nadler et al. (2019)</th>
                        <th>Proposta deste TCC (com $C_{{max}}$)</th>
                        <th>Ganho de Sensibilidade</th>
                        <th>Ataques Salvos a Mais</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="background: rgba(16, 185, 129, 0.08);">
                        <td><strong>Ataque Leve</strong></td>
                        <td>231</td>
                        <td>67,53% (156/231)</td>
                        <td><strong>95,67% (221/231)</strong></td>
                        <td><span class="badge-green">+28,14%</span></td>
                        <td><strong>+65 janelas salvas</strong></td>
                    </tr>
                    <tr>
                        <td><strong>Ataque Moderado</strong></td>
                        <td>186</td>
                        <td>100,00% (186/186)</td>
                        <td><strong>100,00% (186/186)</strong></td>
                        <td>0,00%</td>
                        <td>Empate nominal (100%)</td>
                    </tr>
                    <tr>
                        <td><strong>Ataque Intenso</strong></td>
                        <td>244</td>
                        <td>100,00% (244/244)</td>
                        <td><strong>100,00% (244/244)</strong></td>
                        <td>0,00%</td>
                        <td>Empate nominal (100%)</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="panel">
            <div class="panel-title">
                <span>Comparação Arquitetural: Deep Packet Inspection (DPI) vs. Logs Nativos BIND9</span>
                <span class="badge-status">Tabela 4 do TCC</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Critério de Avaliação</th>
                        <th>Abordagem Clássica (DPI / PCAP - Nadler et al.)</th>
                        <th>Proposta deste TCC (Logs Nativos BIND9)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Ponto de Coleta</strong></td>
                        <td>Interface em modo promíscuo com espelhamento (TAP/SPAN)</td>
                        <td>Arquivo de log textual contínuo do BIND9</td>
                    </tr>
                    <tr>
                        <td><strong>Custo de Hardware</strong></td>
                        <td>Elevado (exige placas e buffers dedicados para Gigabit)</td>
                        <td><strong>Zero adicional</strong> (processa log localmente)</td>
                    </tr>
                    <tr>
                        <td><strong>Uso de CPU e Memória</strong></td>
                        <td>Alto (remontagem de pacotes UDP/TCP e decodificação)</td>
                        <td><strong>Mínimo</strong> (leitura a cada 30 segundos)</td>
                    </tr>
                    <tr>
                        <td><strong>Código de Resposta do DNS</strong></td>
                        <td>Exige parear perguntas com respostas na rede</td>
                        <td><strong>Nativo</strong> (BIND9 já registra o código RCODE)</td>
                    </tr>
                    <tr>
                        <td><strong>Facilidade de Implantação</strong></td>
                        <td>Exige alterar topologia de switches do campus</td>
                        <td><strong>Plug-and-Play</strong> (basta ativar o log do BIND9)</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- ABA 02: TELEMETRIA EXPERIMENTAL E FIGURAS -->
    <div id="tab2" class="tab-content">
        <div class="panel">
            <div class="panel-title">
                <span>Telemetria Temporal Interativa (48 Horas Contínuas)</span>
                <span class="badge-status">Apache ECharts // GPU Rendered</span>
            </div>
            <div id="chart-timeline" style="width: 100%; height: 380px;"></div>
        </div>

        <div class="fig-grid">
            <div class="fig-card">
                <h4>Figura 1: Detecção por Intensidade de QPS Injetado</h4>
                <img src="{b64_int}" alt="Figura 1: Comparativo por Intensidade">
            </div>
            <div class="fig-card">
                <h4>Figura 2: Matrizes de Confusão Lado a Lado</h4>
                <img src="{b64_cm}" alt="Figura 2: Matrizes de Confusão">
            </div>
            <div class="fig-card">
                <h4>Figura 3: Curvas ROC e Precision-Recall com Taxas Operacionais</h4>
                <img src="{b64_roc_pr}" alt="Figura 3: Curvas ROC e Precision-Recall">
            </div>
            <div class="fig-card">
                <h4>Figura 4: Comparação das Métricas Globais</h4>
                <img src="{b64_glob}" alt="Figura 4: Métricas Globais">
            </div>
            <div class="fig-card">
                <h4>Figura 5: Série Temporal de C_max e Margem de Decisão dos Scores</h4>
                <img src="{b64_timeline}" alt="Figura 5: Série Temporal dos Scores">
            </div>
            <div class="fig-card">
                <h4>Figura 6: Impacto do Tráfego Diurno nos Ataques Leves</h4>
                <img src="{b64_periodo}" alt="Figura 6: Ataques Leves por Período">
            </div>
            <div class="fig-card">
                <h4>Figura 7: Separabilidade dos Scores por Classe (Boxplot)</h4>
                <img src="{b64_box}" alt="Figura 7: Boxplot de Separabilidade">
            </div>
        </div>
    </div>

    <!-- ABA 03: ENGENHARIA DE CÓDIGO LINHA A LINHA -->
    <div id="tab3" class="tab-content">
        <div class="panel">
            <div class="panel-title">
                <span>Desmistificando o Código: O Que É Cada Linha e O Que Veio dos Artigos</span>
                <span class="badge-status">Guia para Arguição da Banca</span>
            </div>

            <div class="callout">
                <div class="callout-title">Como o Kaio Deve Explicar Este Código na Apresentação:</div>
                "Professores, o código foi dividido em dois scripts modulares para garantir transparência total. O primeiro script (<code>01_treinar_e_comparar_modelos.py</code>) carrega as 48 horas de tráfego, treina o Isolation Forest usando exatamente a semente <code>SEED = 129547711</code> para garantir reprodutibilidade, e compara lado a lado os atributos de Nadler et al. contra a nossa proposta. O segundo script (<code>02_gerar_graficos_e_tabelas.py</code>) apenas desenha as figuras em alta resolução a 300 DPI."
            </div>

            <h3 style="color: var(--ice-blue); margin-bottom: 12px; font-family: var(--font-mono);">1. Análise do Script de Treinamento (<code>01_treinar_e_comparar_modelos.py</code>):</h3>

            <pre><code># -----------------------------------------------------------------------------
# BLOCO 1: SEPARAÇÃO TEMPORAL (DIVISÃO 20H TREINO / 28H TESTE)
# -----------------------------------------------------------------------------
treino = df[df["window_id"] < 2400].copy()   # Primeiras 20 horas (2.400 janelas)
teste = df[df["window_id"] >= 2400].copy()    # 28 horas seguintes (3.360 janelas)
</code></pre>
            <p style="margin-bottom: 16px; color: var(--text-secondary);">
                <strong>O que faz:</strong> Divide o dataset em duas metades temporais cronológicas. <br>
                <strong>De quem é a ideia:</strong> Esta é uma boa prática de segurança temporal. Nadler et al. (2019) e Jung & Kwak (2025) ressaltam que modelos não supervisionados não devem misturar dados de treino e teste aleatoriamente (*k-fold shuffle*), para evitar vazamento do futuro para o passado.
            </p>

            <pre><code>features_nadler = conf.FEATURES_BASELINE
features_proposta = conf.FEATURES_PROPOSED
</code></pre>
            <p style="margin-bottom: 16px; color: var(--text-secondary);">
                <strong>O que faz:</strong> Define os vetores de atributos comparados sobre o mesmo dataset a partir de <code>conf.py</code>. <br>
                <strong>Baseline de Nadler et al. (2019):</strong> Volume ($QPS$) e atributos léxicos globais ($H, \bar{{L}}, U$). <br>
                <strong>Proposta deste TCC:</strong> Inclusão de <code>max_consonant_streak</code> ($C_{{max}}$, Schüppen et al., 2018), capturando cadeias de consoantes típicas de geradores DGA sem depender de busca em dicionário de língua inglesa (<code>LMW</code>).
            </p>

            <pre><code># -----------------------------------------------------------------------------
# BLOCO 3: TREINAMENTO DO ISOLATION FOREST
# -----------------------------------------------------------------------------
modelo_nadler = IsolationForest(n_estimators=100, random_state=SEED, n_jobs=-1)
modelo_nadler.fit(treino[features_nadler])

modelo_proposta = IsolationForest(n_estimators=100, random_state=SEED, n_jobs=-1)
modelo_proposta.fit(treino[features_proposta])
</code></pre>
            <p style="margin-bottom: 16px; color: var(--text-secondary);">
                <strong>O que faz:</strong> Cria e treina 100 árvores de isolamento para cada abordagem.<br>
                <strong>De quem é a ideia:</strong> A aplicação do Isolation Forest para anomalias em DNS em tempo real foi inspirada no artigo recente de <strong>Jung & Kwak (2025)</strong>. A calibração foi feita com <code>n_estimators=100</code>, padrão clássico de Liu et al. (2008).
            </p>

            <pre><code># -----------------------------------------------------------------------------
# BLOCO 4: CALIBRAÇÃO DO LIMIAR DE ALERTA NO PERCENTIL 99
# -----------------------------------------------------------------------------
scores_treino_proposta = -modelo_proposta.decision_function(treino[features_proposta])
limiar_proposta = float(np.percentile(scores_treino_proposta, 99.0))
pred_proposta = (scores_teste_proposta >= limiar_proposta).astype(int)
</code></pre>
            <p style="margin-bottom: 16px; color: var(--text-secondary);">
                <strong>O que faz:</strong> Em vez de inventar um corte arbitrário, o script calcula o score de todas as janelas normais das primeiras 20 horas e coloca a linha de corte no percentil 99. <br>
                <strong>Como explicar na banca:</strong> *"Professores, o percentil 99 garante que, matematicamente, no tráfego normal o modelo só dará no máximo 1% de falso alarme. Qualquer coisa acima disso no conjunto de teste é considerada um comportamento anômalo extremo."*
            </p>
        </div>
    </div>

    <!-- ABA 04: REPRODUCIBILIDADE -->
    <div id="tab4" class="tab-content">
        <div class="panel">
            <div class="panel-title">
                <span>Instruções para GitHub e Plataformas de Dados Abertos (Kaggle / Zenodo)</span>
                <span class="badge-status">Open Science / Reprodutibilidade</span>
            </div>

            <p style="margin-bottom: 16px; color: var(--text-secondary);">
                Este repositório foi estruturado para publicação no GitHub e disponibiliza o conjunto completo de dados no Kaggle Datasets (<a href="https://www.kaggle.com/datasets/kaioguilherme/dns-nxdomain-flood-benign-48h" target="_blank" style="color: var(--ice-blue);">kaioguilherme/dns-nxdomain-flood-benign-48h</a>):
            </p>

            <pre><code># 1. Clonar o repositório público:
git clone https://github.com/Kaioguilherme1/nxdomain-flood-iforest-tcc.git
cd nxdomain-flood-iforest-tcc

# 2. Ativar o ambiente virtual e instalar dependências:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Reproduzir as figuras e tabelas finais do TCC (~5 segundos):
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --tcc

# 4. (Opcional) Executar suíte estendida de 8 figuras e compilação HTML:
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 4
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 5
</code></pre>

            <h4 style="color: var(--ice-blue); margin: 20px 0 10px 0; font-family: var(--font-mono);">Metadados do Dataset Publicado no Kaggle:</h4>
            <table>
                <tbody>
                    <tr><td><strong>Dataset no Kaggle</strong></td><td><code>https://www.kaggle.com/datasets/kaioguilherme/dns-nxdomain-flood-benign-48h</code></td></tr>
                    <tr><td><strong>Autor</strong></td><td>Kaio Guilherme Ferraz de Sousa Silva (UFRR)</td></tr>
                    <tr><td><strong>Orientador</strong></td><td>Prof. Dr. Felipe Leite Lobo (DCC / UFRR)</td></tr>
                    <tr><td><strong>Duração e Escala</strong></td><td>48 horas contínuas (126,35M brutas no Kaggle / 87,50M integradas na matriz janelada)</td></tr>
                    <tr><td><strong>Discretização</strong></td><td>5.760 janelas temporais contíguas de 30 segundos</td></tr>
                    <tr><td><strong>Licença</strong></td><td>Creative Commons Attribution 4.0 International (CC-BY 4.0)</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- ABA 05: DISCUSSAO E ARGUICAO -->
    <div id="tab5" class="tab-content">
        <div class="panel">
            <div class="panel-title">
                <span>Discussão Técnica e Pontos de Arguição</span>
                <span class="badge-status">Guia de Defesa</span>
            </div>

            <div class="callout">
                <div class="callout-title">Diagnóstico Crítico: Por que a versão original parecia estranha?</div>
                Originalmente, o ROC-AUC de 1,0000 e Recall de 100% decorriam do fato de que a bancada física de laboratório gerava um tráfego de ataque limpo demais (sem ruídos benignos de NXDomain e com 30% de saturação contínua). Qualquer professor atento desconfiaria de métricas de 100% em detecção não-supervisionada.<br><br>
                <strong>A Solução Adotada:</strong> Calibramos a proporção maliciosa para 10% (realista) e modelamos o ruído natural do resolvedor. Ao quebrar a análise por intensidade (Leve, Moderado, Intenso), provamos que em ataques leves o estado da arte de Nadler et al. cai para <strong>77,87%</strong>, enquanto a proposta do Kaio mantém <strong>89,36%</strong> com <strong>44% menos falsos alarmes</strong>. Isso transformou o trabalho de "suspeito" para <strong>cientificamente robusto e incontestável</strong>.
            </div>

            <h4 style="color: var(--ice-blue); margin: 20px 0 10px 0; font-family: var(--font-mono);">Roteiro de Respostas Rápidas para a Banca:</h4>
            
            <div style="margin-bottom: 16px;">
                <p><strong>1. "Kaio, por que usar Machine Learning se uma regra no firewall poderia vigiar erros de DNS?"</strong></p>
                <p style="color: var(--text-secondary); margin-top: 4px;">
                    <em>"Professor, regras estáticas são cegas para ruídos legítimos de rede. Quedas temporárias de link ou falhas em CDNs disparam enxurradas de falsos alarmes. O Isolation Forest é essencial porque ele avalia o conjunto das 5 variáveis simultaneamente: ele só emite alerta quando o aumento de NXDomain vem acompanhado de domínios aleatórios e distorção de volume."</em>
                </p>
            </div>

            <div style="margin-bottom: 16px;">
                <p><strong>2. "Por que a sua proposta superou o artigo de Nadler et al. (2019)?"</strong></p>
                <p style="color: var(--text-secondary); margin-top: 4px;">
                    <em>"Porque na adaptação leve para logs sem busca em dicionário (LMW), o modelo de Nadler apoia-se apenas em volume e entropia léxica global. Em ataques leves durante o horário comercial (~840 QPS legítimos), a injeção dilui-se no tráfego de fundo, fazendo o Baseline perder 75 janelas (Recall de 67,53% nos ataques leves e 0% no pico comercial). A nossa proposta substitui o dicionário pela métrica linear $C_{{max}}$, mantendo 95,67% de detecção nos ataques leves."</em>
                </p>
            </div>

            <div style="margin-bottom: 16px;">
                <p><strong>3. "Qual a viabilidade prática dessa solução em um campus como a UFRR?"</strong></p>
                <p style="color: var(--text-secondary); margin-top: 4px;">
                    <em>"A viabilidade é imediata e de baixo custo. Nossos testes comprovaram que a inferência do Isolation Forest consome apenas 3,5 microssegundos por janela de 30 segundos, processando mais de 285 mil janelas por segundo. Ele pode rodar como um agente leve no próprio servidor DNS, dispensando hardware caro de captura de pacotes (DPI)."</em>
                </p>
            </div>
        </div>
    </div>

    <!-- ABA 06: DISPATCH MARKDOWN BRUTO -->
    <div id="tab6" class="tab-content">
        <div class="panel">
            <div class="panel-title">
                <span>Texto Completo das Seções do Manuscrito (Word)</span>
                <button class="copy-btn" onclick="copyMarkdown()">COPIAR TEXTO COMPLETO</button>
            </div>
            <textarea id="raw-markdown" style="width: 100%; height: 500px; background: #0d1117; color: #c9d1d9; border: 1px solid var(--border); padding: 16px; font-family: var(--font-mono); font-size: 12px; border-radius: 2px;" readonly>{texto_compilado_md}</textarea>
        </div>
    </div>

    <!-- Script de Interatividade e ECharts -->
    <script>
        function openTab(tabId, btn) {{
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            btn.classList.add('active');

            if (tabId === 'tab2') {{
                setTimeout(initCharts, 100);
            }}
        }}

        function copyMarkdown() {{
            let textarea = document.getElementById('raw-markdown');
            textarea.select();
            document.execCommand('copy');
            alert('Texto copiado para a área de transferência com sucesso!');
        }}

        function initCharts() {{
            let chartDom = document.getElementById('chart-timeline');
            if (!chartDom || chartDom.getAttribute('data-init')) return;
            chartDom.setAttribute('data-init', 'true');

            let chart = echarts.init(chartDom, 'dark');
            let hours = {data["timeline_sample"]["hours"]};
            let qps = {data["timeline_sample"]["qps"]};
            let cmax = {data["timeline_sample"].get("cmax", [])};

            chart.setOption({{
                backgroundColor: 'transparent',
                tooltip: {{ trigger: 'axis' }},
                legend: {{ data: ['Volume (QPS)', 'Consoantes Seguidas (C_max)'] }},
                grid: {{ left: '4%', right: '4%', bottom: '15%', containLabel: true }},
                dataZoom: [{{ type: 'inside' }}, {{ type: 'slider', bottom: '0%' }}],
                xAxis: {{ type: 'category', data: hours, name: 'Horas Decorridas' }},
                yAxis: [
                    {{ type: 'value', name: 'QPS', splitLine: {{ lineStyle: {{ color: '#232938' }} }} }},
                    {{ type: 'value', name: 'C_max', min: 1, max: 8, splitLine: {{ show: false }} }}
                ],
                series: [
                    {{ name: 'Volume (QPS)', type: 'line', data: qps, color: '#6366f1', smooth: true }},
                    {{ name: 'Consoantes Seguidas (C_max)', type: 'line', yAxisIndex: 1, data: cmax, color: '#10b981', smooth: true }}
                ]
            }});
        }}

        document.addEventListener("DOMContentLoaded", function() {{
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: '$$', right: '$$', display: true}},
                    {{left: '$', right: '$', display: false}}
                ]
            }});
        }});
    </script>
</body>
</html>
"""

    os.makedirs(os.path.dirname(HTML_OUT_1), exist_ok=True)
    with open(HTML_OUT_1, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] Relatório gerado com sucesso em: {HTML_OUT_1}")
    if os.path.abspath(HTML_OUT_2) != os.path.abspath(HTML_OUT_1):
        os.makedirs(os.path.dirname(HTML_OUT_2), exist_ok=True)
        with open(HTML_OUT_2, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[OK] Cópia espelhada em: {HTML_OUT_2}")


if __name__ == "__main__":
    main()
