# Arquitetura de Pipelines e Scripts (MLOps)

**Projeto:** Detecção de Ataques NXDOMAIN Flood em Servidores DNS Utilizando Isolation Forest  
**Instituição:** Universidade Federal de Roraima (UFRR) — Departamento de Ciência da Computação (DCC)  
**Autor:** Kaio Guilherme Ferraz de Sousa Silva | **Orientador:** Prof. Dr. Felipe Leite Lobo  
**Semente Global (RNG):** `SEED = 129547711`  
**Dataset Completo (Kaggle):** https://www.kaggle.com/datasets/kaioguilherme/dns-nxdomain-flood-benign-48h

---

## 1. Estrutura dos Módulos

```text
05_Codigo_e_Scripts/
├── 01_coleta_e_simulacao/         <- Bancada Docker BIND 9.18 + script de ataque (dnsperf)
├── 02_pipeline_preparacao_dados/   <- Normalização de IPs, particionamento, validação e CSV.gz
├── 03_engenharia_de_features/      <- Agregação em janelas de 30 s [QPS, C_max, H, L, U]
├── 04_treinamento_ia_e_avaliacao/  <- Treinamento One-Class (Isolation Forest) e figuras 300 DPI
├── 05_relatorios_e_visualizacao/   <- Compilador HTML interativo standalone
├── conf.py                         <- Parâmetros, caminhos e hiperparâmetros oficiais
└── run_pipeline_completo.py        <- Orquestrador mestre via CLI
```

---

## 2. Descrição dos Módulos

### `01_coleta_e_simulacao/`
* **`nxdomain-script/campanha-nxdomain.py`**: Automação de 21 campanhas controladas de *NXDOMAIN Flood* via `dnsperf` (Leve, Moderado e Intenso) contra o BIND 9 em rede isolada (`192.168.2.0/24`).
* **`lab_reproduzivel/`**: Infraestrutura `docker-compose.yml` com ISC BIND 9.18 e instruções para conectar o repositório irmão `dns-log-generator`.

### `02_pipeline_preparacao_dados/`
* **`01_normalizar_ataques_ips.py`**: Remapeamento determinístico (`SEED = 129547711`) de portas efêmeras e IPs de origem (60% internos `10.0.0.0/16` / 40% externos) apenas para verossimilhança do log bruto (IPs não são usados como atributos no modelo).
* **`02_particionar_logs_dataset.py`**: Particionamento e auditoria por dia e por campanha.
* **`03_validar_coerencia_temporal.py`**: Validação da contiguidade temporal das 48h e da sintaxe `query:` do BIND 9.
* **`04_estruturar_logs_para_csv.py`**: Parser em *streaming* que gera `dns_eventos_estruturados_48h.csv.gz` e a amostra de 100k linhas em `06_Datasets_e_Logs/02_dataset_refinado/`.
* **`extrair_ips_benignos.sh`**: Utilitário Bash/AWK para listagem dos 25.000 IPs únicos benignos.

### `03_engenharia_de_features/`
* **`extrair_features_janeladas.py`**: Discretiza o fluxo em janelas contíguas de $\Delta t = 30\text{ s}$ (`5.760` janelas) calculando exclusivamente a partir dos registros `query:`:
  * `qps`: Consultas por segundo ($N_{\text{total}} / 30$).
  * `max_consonant_streak` ($C_{\max}$): Média da maior sequência de consoantes consecutivas no primeiro rótulo do subdomínio (Schüppen et al., 2018).
  * `entropy` ($H$): Entropia de Shannon dos caracteres dos subdomínios.
  * `mean_fqdn_len` ($L$): Comprimento médio em caracteres dos FQDNs consultados.
  * `unique_ratio` ($U$): Razão entre domínios distintos e o total de consultas na janela.

### `04_treinamento_ia_e_avaliacao/`
* **`gerar_artefatos_tcc_simplificado.py`**: Script unificado que lê `dataset_features_48h_w30s.csv` e gera em ~5 segundos exatamente as **4 Figuras** (`Figura_1_...` a `Figura_4_...`) e **3 Tabelas** (`Tabela_3_...` a `Tabela_5_...`) em `07_Resultados_e_Relatorios/03_Artefatos_Finais_TCC/`.
* **`01_treinar_e_comparar_modelos.py`**: Treina ambos os modelos (*Baseline* de Nadler et al., 2019 e Proposta com $C_{\max}$) com `100` árvores nas primeiras `2.400` janelas (`20 h` nominais), calibra $\tau$ no percentil `99,4%` e exporta métricas globais, por intensidade e por campanha em `07_Resultados_e_Relatorios/02_Tabelas_e_Metricas/`.
* **`02_gerar_graficos_e_tabelas.py`**: Gera a suíte estendida de 8 figuras científicas (300 DPI) em `07_Resultados_e_Relatorios/01_Figuras_TCC/`.
* **`03_gerar_figura_arvore_isolamento.py`**: Calcula a profundidade média empírica (`decision_path`) nas 100 *iTrees* e gera `Figura_01_mecanismo_isolamento_itree.png`.

### `05_relatorios_e_visualizacao/`
* **`compilar_relatorio_html.py`**: Compila o painel analítico HTML standalone (`07_Resultados_e_Relatorios/relatorio_geral_estatistica_e_ml.html`).

---

## 3. Guia de Execução

```bash
# 1. Verificar arquivos presentes nas camadas de dados e resultados
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --status

# 2. Gerar exatamente as 4 figuras e 3 tabelas do texto final do TCC (~5s)
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --tcc

# 3. Executar etapas específicas
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 1  # Validação temporal dos logs (requer Kaggle)
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 2  # Parser BIND 9 -> CSV.gz (requer Kaggle)
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 3  # Extração de janelas de 30s (requer CSV.gz)
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 4  # Treino + 8 figuras + artefatos finais do TCC
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --step 5  # Compilação do relatório HTML standalone

# 4. Pipeline completo do zero (requer os logs brutos do Kaggle em 06_Datasets_e_Logs/01_dataset_bruto/)
python3 05_Codigo_e_Scripts/run_pipeline_completo.py --all
```
