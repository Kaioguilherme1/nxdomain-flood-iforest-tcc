# Documentação Metodológica: Dataset Estruturado em Formato Tabular (Event-Level CSV)

**Projeto:** Detecção de Anomalias em Logs DNS utilizando Aprendizado de Máquina  
**Instituição:** Universidade Federal de Roraima (UFRR) - Departamento de Ciência da Computação (DCC)  
**Autor:** Kaio Guilherme Ferraz de Sousa Silva  
**Orientador:** Prof. Dr. Felipe Lobo  
**Script Gerador:** [`05_Codigo_e_Scripts/02_pipeline_preparacao_dados/04_estruturar_logs_para_csv.py`](../../05_Codigo_e_Scripts/02_pipeline_preparacao_dados/04_estruturar_logs_para_csv.py)  

---

## 1. Justificativa Científica e Arquitetura do Pipeline

Na literatura de análise de tráfego passivo de DNS (*Passive DNS Analysis*) e detecção de anomalias (Bilge et al., 2014; Nadler et al., 2019), servidores recursivos corporativos registram eventos em logs textuais não estruturados (como o formato padrão do ISC BIND9).

Para que algoritmos de aprendizado de máquina, modelos estatísticos e extratores de janelas deslizantes possam operar com alta eficiência computacional ($O(1)$ de acesso por registro), o fluxo de eventos brutos deve ser decomposto em **atributos atômicos tabulares** enriquecidos com a anotação supervisionada de *Ground Truth*:

```text
[Log BIND9 Bruto] (Texto livre)
       │
       ▼  (Fast String Parsing + Timestamp Unix Epoch + 2-Way Merge)
[Dataset Tabular Estruturado] (CSV / Parquet)
       ├── Atributos de Identificação: datetime, epoch, client_ptr
       ├── Atributos de Rede e Transporte: client_ip, client_port, resolver_ip
       ├── Atributos da Consulta DNS: domain, qtype, flags
       └── Rótulo Supervisionado: label (0 = Normal, 1 = Ataque)
```

---

## 2. Dicionário de Colunas e Especificação de Tipos

| Ordem | Nome da Coluna | Tipo de Dado | Exemplo | Descrição Técnica |
| :---: | :--- | :---: | :--- | :--- |
| **1** | `datetime` | `String (ISO/BIND)` | `07-Jun-2026 20:00:22.302` | Timestamp legível com resolução de milissegundos. |
| **2** | `timestamp_epoch` | `Float64` | `1780862422.302` | Época Unix contínua para indexação temporal rápida e ordenação. |
| **3** | `client_ip` | `String (IPv4)` | `10.0.135.233` ou `219.250.253.46` | Endereço IP de origem do requisitante (nó interno ou externo). |
| **4** | `client_port` | `UInt16` | `58349` | Porta de origem efêmera gerada deterministicamente $[49152, 65535]$. |
| **5** | `client_ptr` | `String (Hex)` | `0x75b39630a5ab` | Ponteiro de buffer do cliente alocado no resolvedor recursivo. |
| **6** | `domain` | `String (FQDN)` | `pcptxeogptbmwnnuhv.info` | Domínio ou FQDN consultado (alvo do ataque ou requisição legítima). |
| **7** | `qtype` | `Categorical` | `A`, `AAAA`, `TXT`, `CNAME` | Tipo de registro da consulta DNS. |
| **8** | `flags` | `String` | `+E(0)` | Flags de extensão de protocolo EDNS0 informadas pelo cliente. |
| **9** | `resolver_ip` | `String (IPv4)` | `192.168.0.10` | IP do resolvedor recursivo interno que atendeu a requisição. |
| **10** | `label` | `UInt8 (Binário)` | `0` ou `1` | **Ground Truth:** `0` = Tráfego Benigno / `1` = NXDomain Flood. |

---

## 3. Semântica da Flag de Controle (`label: 0 / 1`)

* **`label = 0` (Tráfego Normal / Benigno):**
  * Representa consultas genuínas de usuários corporativos e acadêmicos modelados pelo `dns-log-generator`.
  * Engloba 25.000 IPs internos da sub-rede `10.0.0.0/16` distribuídos em 5 perfis de uso (alunos, funcionários, desenvolvedores, VPN, dispositivos móveis).
  * Inclui comportamento sazonal realista com ciclos diurnos, picos de horário comercial, pausas para almoço e redução de volume na madrugada.

* **`label = 1` (Tráfego Maligno / NXDomain Flood):**
  * Representa consultas disparadas pelas **21 campanhas de ataque** injetadas via `dnsperf`.
  * Os domínios são subdomínios aleatórios de alta entropia visando saturar a memória cache do servidor recursivo e provocar rajadas de respostas NXDomain do autoritativo.
  * **Distribuição Híbrida de IPs na Integração:** 60% dos eventos com `label = 1` recebem IPs da própria rede interna (`10.0.0.0/16`) e 40% recebem IPs externos para integração realista no log unificado (os IPs não são utilizados como atributo de treinamento).

---

## 4. Como Carregar e Utilizar o Dataset (Exemplos em Python)

### 4.1 Carregamento Rápido da Amostra (100.000 eventos)
```python
import pandas as pd

# Carregar amostra para análise exploratória
df_sample = pd.read_csv("06_Datasets_e_Logs/02_dataset_refinado/dns_eventos_estruturados_amostra.csv")

print(f"Total de registros: {len(df_sample):,}")
print(df_sample['label'].value_counts())
```

### 4.2 Leitura do Dataset Completo de 48 Horas em Streaming / Chunks
```python
import pandas as pd

# Leitura direta do arquivo comprimido .csv.gz em pedaços de 1.000.000 linhas
chunk_size = 1_000_000
for i, chunk in enumerate(pd.read_csv("06_Datasets_e_Logs/02_dataset_refinado/dns_eventos_estruturados_48h.csv.gz", 
                                     compression="gzip", chunksize=chunk_size)):
    print(f"Processando bloco {i+1}: {len(chunk)} linhas | Ataques: {(chunk['label'] == 1).sum()}")
    # Extrair estatísticas ou calcular vetores de atributos...
```

---

## 5. Fundamentação Científica nos Artigos de Referência

A estruturação tabular por evento com rótulo binário $y \in \{0, 1\}$ é o requisito primário preconizado pelos principais trabalhos da área:

1. **Nadler et al. (2019) — *Detection of Malicious Data Exfiltration Over DNS*:**
   O artigo demonstra que métodos de detecção de anomalias não podem confiar em regras estáticas de firewall ou inspeção de carga útil criptografada. O modelo exige dados tabulares normalizados com timestamps contínuos para permitir a divisão em janelas deslizantes não sobrepostas $\lambda = 60\text{ min}$ e agregação de atributos estatísticos de volume e comprimento.

2. **Bilge et al. (2014) — *EXPOSURE: Finding Malicious Domains Using Passive DNS*:**
   Define as métricas de domínio (comprimento médio do rótulo, fração de caracteres numéricos e contagem de domínios distintos) calculadas a partir de registros tabulares contendo `client_ip`, `domain` e `timestamp`.

3. **Al-Musawi et al. (2018) — *Detecting DNS Flood and Amplification Attacks*:**
   Destaca a importância de isolar eventos por tupla de transporte `(client_ip, client_port, resolver_ip)` e registrar flags de protocolo EDNS0 para quantificar o impacto de ataques de negação de serviço na infraestrutura recursiva.
