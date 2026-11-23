"""
Arquivo central de configuracao experimental do pipeline de deteccao de anomalias DNS.
Concentra caminhos, hiperparametros do modelo, recortes temporais e definicoes de atributos.
"""

import os
import sys

# Diretorios base do projeto
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPTS_DIR)
DATA_DIR = os.path.join(BASE_DIR, "06_Datasets_e_Logs")

# Subdiretorios de dados por camada (Bronze, Silver, Gold e Metadados)
RAW_LOGS_DIR = os.path.join(DATA_DIR, "01_dataset_bruto")
REFINED_DIR = os.path.join(DATA_DIR, "02_dataset_refinado")
FEATURES_DIR = os.path.join(DATA_DIR, "03_dataset_final_features")
METADATA_DIR = os.path.join(DATA_DIR, "04_metadados_ground_truth")

# Diretorios de saida para figuras, tabelas e relatorios
RESULTS_DIR = os.path.join(BASE_DIR, "07_Resultados_e_Relatorios")
RESULTS_FIGURES_DIR = os.path.join(RESULTS_DIR, "01_Figuras_TCC")
RESULTS_TABLES_DIR = os.path.join(RESULTS_DIR, "02_Tabelas_e_Metricas")
FINAL_TCC_ARTIFACTS_DIR = os.path.join(RESULTS_DIR, "03_Artefatos_Finais_TCC")
FIGURES_DIR = RESULTS_FIGURES_DIR
REPORTS_DIR = RESULTS_DIR

# Arquivos de entrada e saida principais
BENIGN_LOG_PATH = os.path.join(RAW_LOGS_DIR, "benigno_unificado.log")
ATTACK_LOG_PATH = os.path.join(RAW_LOGS_DIR, "ataques_unificados.log")
STRUCTURED_CSV_GZ = os.path.join(REFINED_DIR, "dns_eventos_estruturados_48h.csv.gz")
STRUCTURED_SAMPLE_CSV = os.path.join(REFINED_DIR, "dns_eventos_estruturados_amostra.csv")
DATASET_OFFICIAL_PATH = os.path.join(FEATURES_DIR, "dataset_features_48h_w30s.csv")
CAMPAIGNS_CSV_PATH = os.path.join(METADATA_DIR, "ataques_campanhas.csv")

# Interpretador Python ativo (herda o ambiente virtual do usuario)
PYTHON_ML_BIN = sys.executable

# Semente pseudoaleatoria global para reprodutibilidade deterministica do experimento
SEED = 129547711

# Parametros de discretizacao temporal e divisao treino/teste
WINDOW_SIZE_SEC = 30          # Duracao de cada janela deslizante em segundos (Delta t)
TOTAL_HOURS = 48              # Duracao total do experimento continuo em horas
TOTAL_WINDOWS = 5760          # Total de janelas de 30s ao longo de 48h
TRAIN_WINDOWS = 2400          # Primeiras 20h (2.400 janelas) exclusivas de trafego normal para treino
TEST_WINDOWS = 3360           # 28h restantes (3.360 janelas) contendo trafego misto e 21 campanhas

# Definicao dos modelos avaliados no mesmo conjunto de dados
MODEL_BASELINE_NAME = "Baseline (Nadler et al., 2019)"
MODEL_PROPOSED_NAME = "Proposta deste TCC (com C_max)"

# Vetor de atributos do modelo Baseline de Nadler et al. (2019): volume e estatistica lexica basica
FEATURES_BASELINE = [
    "qps",                    # Taxa de consultas por segundo na janela (N_total / Delta t)
    "entropy",                # Entropia de Shannon dos caracteres dos subdominios (bits)
    "mean_fqdn_len",          # Comprimento medio em caracteres dos dominios consultados
    "unique_ratio",           # Razao entre dominios distintos e total de consultas na janela
]

# Vetor de atributos da Proposta deste TCC: adiciona a maior sequencia de consoantes consecutivas
# Referencia: Schuppen et al. (USENIX Security, 2018) - substitui busca em dicionario (LMW) em O(|s|)
FEATURES_PROPOSED = [
    "qps",                    # Taxa de consultas por segundo na janela
    "max_consonant_streak",   # Media da maior sequencia de consoantes seguidas no subdominio (C_max)
    "entropy",                # Entropia de Shannon dos caracteres dos subdominios
    "mean_fqdn_len",          # Comprimento medio dos dominios consultados
    "unique_ratio",           # Razao de dominios unicos na janela
]

# Parametros reais das campanhas de ataque adquiridos via dnsperf (campanha-nxdomain.py)
VOWELS = frozenset("aeiou")
CLIENTS_BY_LEVEL = {
    "LEVE": 10,               # 10 clientes concorrentes (-c 10, duracao 10 min / 600s)
    "MODERADO": 40,           # 40 clientes concorrentes (-c 40, duracao 15 min / 900s)
    "INTENSO": 100,           # 100 clientes concorrentes (-c 100, duracao 30 min / 1800s)
}
LIMITS_QUERIES_BY_LEVEL = {
    "LEVE": (320, 620),       # Faixa de consultas de ataque por janela de 30s no perfil Leve
    "MODERADO": (1600, 2800), # Faixa de consultas de ataque por janela de 30s no perfil Moderado
    "INTENSO": (6000, 9000),  # Faixa de consultas de ataque por janela de 30s no perfil Intenso
}

# Hiperparametros do algoritmo Isolation Forest e calibracao de limiar operacional
IF_N_ESTIMATORS = 100         # Quantidade de arvores de isolamento (iTrees) na floresta
IF_MAX_SAMPLES = "auto"       # Amostragem padrao por arvore (min(256, n_samples))
IF_N_JOBS = -1                # Paralelizacao em todos os nucleos disponiveis
THRESHOLD_PERCENTILE = 99.4   # Percentil de corte nos scores de treino para FAR operacional < 1.0%

# Parametros de exportacao grafica (padrao de publicacao academica)
PLOT_DPI = 300
FONT_FAMILY = "DejaVu Sans"
COLOR_BASELINE = "#94a3b8"    # Cinza ardosia para o Baseline de Nadler et al. (2019)
COLOR_PROPOSED = "#4338ca"    # Azul indico para o modelo proposto neste TCC
COLOR_ALERT = "#dc2626"       # Vermelho para limiares de decisao e faixas de ataque
