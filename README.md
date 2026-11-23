# nxdomain-flood-iforest-tcc

Pipeline reprodutível de detecção não supervisionada de ataques *NXDOMAIN Flood* (DGA *QakBot*) em registros `query log` do **ISC BIND 9** utilizando **Isolation Forest** com o atributo fonotático de sequência máxima de consoantes consecutivas ($C_{\max}$).

Código-fonte, configurações de bancada virtualizada (`BIND 9.18 + dnsperf`), matriz oficial de características (`dataset_features_48h_w30s.csv`) e artefatos experimentais do Trabalho de Conclusão de Curso (DCC/UFRR):

> **Detecção de Ataques NXDOMAIN Flood em Servidores DNS Utilizando Isolation Forest**  
> **Autor:** Kaio Guilherme Ferraz de Sousa Silva | **Orientador:** Prof. Dr. Felipe Leite Lobo

---

## Ecossistema do Experimento

| Recurso | Localização | Conteúdo e Finalidade |
| :--- | :--- | :--- |
| **Código e Matriz Janelada** | Este repositório (`nxdomain-flood-iforest-tcc`) | Scripts completos, bancada Docker e `dataset_features_48h_w30s.csv` (reproduz gráficos e tabelas do TCC em segundos). |
| **Dataset Completo (48h Brutas)** | [Kaggle: kaioguilherme/dns-nxdomain-flood-benign-48h](https://www.kaggle.com/datasets/kaioguilherme/dns-nxdomain-flood-benign-48h) | Logs brutos BIND 9 (`benigno_unificado.log`, `ataques_unificados.log`) e CSV tabular estruturado (`dns_eventos_estruturados_48h.csv.gz`). |
| **Gerador de Tráfego Benigno** | [GitHub: Kaioguilherme1/dns-log-generator](https://github.com/Kaioguilherme1/dns-log-generator) | Simulador estocástico determinístico (`SEED = 129547711`) que gerou as 48h de tráfego legítimo de 25.000 clientes. |

---

## Reprodução Rápida (~5 segundos — Gráficos e Tabelas do TCC)

A matriz oficial janelada (`06_Datasets_e_Logs/03_dataset_final_features/dataset_features_48h_w30s.csv`, com `5.760` janelas de `30 s`) já acompanha este repositório. Você consegue reproduzir **exatamente todos os gráficos e tabelas do texto final do TCC** sem precisar baixar os gigabytes de logs brutos:

### Passo a passo
```bash
# 1. Clonar o repositório
git clone https://github.com/Kaioguilherme1/nxdomain-flood-iforest-tcc.git
cd nxdomain-flood-iforest-tcc

# 2. Criar e ativar o ambiente virtual Python
python3 -m venv .venv
source .venv/bin/activate        # No Windows: .venv\Scripts\activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Gerar exatamente as 4 figuras e 3 tabelas do texto final do TCC
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --tcc
# (Equivalente a: python3 05_Codigo_e_Scripts/04_treinamento_ia_e_avaliacao/gerar_artefatos_tcc_simplificado.py)
```

Os artefatos finais serão gravados em `07_Resultados_e_Relatorios/03_Artefatos_Finais_TCC/`:

| Arquivo gerado em `03_Artefatos_Finais_TCC/` | Correspondência no Manuscrito (TCC) |
| :--- | :--- |
| `Figura_1_mecanismo_isolamento.png` | **Figura 1** — Mecanismo de isolamento na *iTree* e profundidade média empírica |
| `Figura_2_matrizes_confusao.png` | **Figura 2** — Matrizes de confusão comparativas (*Baseline* vs. Proposta) |
| `Figura_3_recall_por_intensidade.png` | **Figura 3** — *Recall* estratificado por intensidade (Leve, Moderado, Intenso) |
| `Figura_4_diluicao_diurna_ataque_leve.png` | **Figura 4** — Impacto da diluição diurna nos ataques leves (08h–17h vs. Madrugada) |
| `Tabela_3_campanhas_ataque.csv` | **Tabela 3** — Parametrização das 21 campanhas `dnsperf` e carga integrada |
| `Tabela_4_desempenho_global.csv` | **Tabela 4** — Comparativo global de métricas (28h de teste / 3.360 janelas) |
| `Tabela_5_atributos_por_intensidade.csv` | **Tabela 5** — Médias dos 5 atributos no tráfego normal e por intensidade |

### Suíte Estendida (8 Figuras + Relatório Interativo HTML)
```bash
# Gera todas as tabelas detalhadas por campanha e as 8 figuras científicas (300 DPI)
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 4

# Compila o painel analítico HTML standalone (Apache ECharts + figuras base64)
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 5
```

---

## Reprodução Completa com o Dataset do Kaggle (Dos Logs Brutos ao Modelo)

Como os logs brutos e o arquivo estruturado excedem o limite de tamanho por arquivo do GitHub, eles estão hospedados publicamente no Kaggle:

> **Dataset oficial no Kaggle:** https://www.kaggle.com/datasets/kaioguilherme/dns-nxdomain-flood-benign-48h

### Nota de transparência sobre a volumetria (Kaggle vs. Matriz do TCC)
- **Captura bruta de estresse no Kaggle (`01_logs_brutos/` e `02_dataset_estruturado/`):** Contém `126.351.730` linhas brutas (`89.174.860` benignas + `37.176.870` de ataque coletadas em estresse contínuo de `dnsperf`) e `122.786.098` eventos no CSV tabular compactado.
- **Matriz janelada oficial do TCC (`dataset_features_48h_w30s.csv`):** Integra exatamente **87.505.371** consultas processadas nas 48h (`85.198.593` benignas + `2.306.778` de ataque escalonadas proporcionalmente em `5.760` janelas de `30 s`, conforme a **Tabela 3** do TCC e os limites `LIMITS_QUERIES_BY_LEVEL` em `05_Codigo_e_Scripts/conf.py`).

### Como baixar e rodar do zero
1. Baixe os arquivos em **https://www.kaggle.com/datasets/kaioguilherme/dns-nxdomain-flood-benign-48h**:
   * **A partir dos logs brutos BIND 9:** coloque `benigno_unificado.log` e `ataques_unificados.log` em `06_Datasets_e_Logs/01_dataset_bruto/`.
   * **Ou direto do CSV tabular estruturado:** coloque `dns_eventos_estruturados_48h.csv.gz` em `06_Datasets_e_Logs/02_dataset_refinado/` e rode a partir da Etapa 3.
2. Execute o pipeline pela linha de comando:
   ```bash
   # Conferir quais camadas estão presentes localmente
   python3 05_Codigo_e_Scripts/run_pipeline_completo.py --status

   # Rodar etapas específicas (1: validação, 2: logs->csv.gz, 3: janelas 30s, 4: treino+figuras, 5: HTML)
   python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 3
   python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 4

   # Ou executar todas as etapas de uma vez (requer os logs brutos na camada 01)
   python3 05_Codigo_e_Scripts/run_pipeline_completo.py --all
   ```

### Recriar a bancada virtualizada (BIND 9 + dnsperf)
Consulte as instruções completas em [`05_Codigo_e_Scripts/01_coleta_e_simulacao/lab_reproduzivel/README_REPLICACAO.md`](05_Codigo_e_Scripts/01_coleta_e_simulacao/lab_reproduzivel/README_REPLICACAO.md), utilizando o repositório irmão [dns-log-generator](https://github.com/Kaioguilherme1/dns-log-generator) e os domínios DGA *QakBot* gerados via [baderj/domain_generation_algorithms](https://github.com/baderj/domain_generation_algorithms).

---

## Arquitetura do Repositório

```text
nxdomain-flood-iforest-tcc/
├── 05_Codigo_e_Scripts/
│   ├── conf.py                                  # Parâmetros oficiais (SEED=129547711, Δt=30s, τ=99,4%)
│   ├── run_pipeline_completo.py                 # Orquestrador CLI (--status, --tcc, --step, --all)
│   ├── 01_coleta_e_simulacao/
│   │   ├── lab_reproduzivel/                    # Docker Compose + named.conf (ISC BIND 9.18)
│   │   └── nxdomain-script/                     # campanha-nxdomain.py (21 campanhas via dnsperf)
│   ├── 02_pipeline_preparacao_dados/            # Normalização de IPs, validação temporal e CSV.gz
│   ├── 03_engenharia_de_features/               # Extração em janelas de 30 s [QPS, C_max, H, L, U]
│   ├── 04_treinamento_ia_e_avaliacao/
│   │   ├── gerar_artefatos_tcc_simplificado.py  # Gera exatamente as 4 figuras e 3 tabelas do TCC
│   │   ├── 01_treinar_e_comparar_modelos.py     # Treino One-Class e tabelas por campanha
│   │   ├── 02_gerar_graficos_e_tabelas.py       # Suíte gráfica estendida (8 figuras em 300 DPI)
│   │   └── 03_gerar_figura_arvore_isolamento.py # Figura 1 (profundidade de corte nas iTrees)
│   └── 05_relatorios_e_visualizacao/            # Compilador do relatório HTML interativo
├── 06_Datasets_e_Logs/
│   ├── 01_dataset_bruto/                        # Pasta de destino dos .log do Kaggle (não versionados)
│   ├── 02_dataset_refinado/                     # Pasta de destino do .csv.gz + manifesto e dicionário
│   ├── 03_dataset_final_features/
│   │   └── dataset_features_48h_w30s.csv        # Matriz oficial (5.760 janelas, 642 KB)
│   └── 04_metadados_ground_truth/               # Campanhas, IPs e auditoria temporal
├── 07_Resultados_e_Relatorios/
│   ├── 01_Figuras_TCC/                          # Suíte completa de 8 figuras (300 DPI)
│   ├── 02_Tabelas_e_Metricas/                   # CSVs e JSONs consolidados
│   └── 03_Artefatos_Finais_TCC/                 # Exatamente as Figuras 1–4 e Tabelas 3–5 do TCC
└── requirements.txt
```

---

## Resultados Esperados na Reprodução (28h de Teste — 3.360 Janelas de 30 s)

Parâmetros de treino: primeiras `20 h` (`2.400` janelas estritamente nominais, `One-Class`), `100` *iTrees*, `SEED = 129547711`, calibração de limiar $\tau$ no percentil `99,4%` do treino ($\tau_{\text{Proposta}} = 0{,}6252$; $\tau_{\text{Baseline}} = 0{,}6256$).

| Métrica | *Baseline* (Nadler et al., 2019) | Proposta deste TCC (com $C_{\max}$) | Variação |
| :--- | :---: | :---: | :---: |
| **Atributos** | `4` (`QPS, H, L, U`) | `5` (`QPS, C_max, H, L, U`) | `+1` |
| **Acurácia Global** | `96,99%` | **`98,96%`** | `+1,97 p.p.` |
| **Precisão** | `95,75%` | **`96,30%`** | `+0,55 p.p.` |
| **Recall Global** | `88,65%` | **`98,49%`** | **`+9,84 p.p.`** |
| **F1-Score** | `92,07%` | **`97,38%`** | **`+5,31 p.p.`** |
| **FAR (Falsos Alarmes)** | `0,96%` (`26 FP`) | **`0,93%` (`25 FP`)** | `-0,03 p.p.` (`< 1%`) |
| **Ataques Perdidos (FN)** | `75 janelas` | **`10 janelas`** | **`-86,7%`** (`-65 FN`) |
| **AUC-ROC / AUC-PR** | `0,9922` / `0,9750` | **`0,9995` / `0,9980`** | `+0,0073` / `+0,0230` |
| **Ataque Leve — Horário Comercial (08h–17h)** | `0,00%` (`0/63`) | **`84,13%` (`53/63`)** | **`+84,13 p.p.`** |
