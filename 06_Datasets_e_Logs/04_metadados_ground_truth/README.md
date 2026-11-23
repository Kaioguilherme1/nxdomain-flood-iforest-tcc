# Camada 04: Metadados e Ground Truth (Audit & Metadata)

**Objetivo:** Garantir transparência, rastreabilidade forense, integridade criptográfica e parâmetros de reprodutibilidade para a monografia.

---

## 1. Arquivos Contidos

| Arquivo | Descrição |
| :--- | :--- |
| **`ataques_campanhas.csv`** | Tabela com início e término em milissegundos das 21 campanhas de ataque injetadas simultaneamente pelo `dnsperf` (5 QPS, 25 QPS e 100 QPS), incluindo duração observada, QPS médio e distribuição de IPs internos e externos (`ips_internos, ips_externos`). |
| **`ataques_ips.csv`** | Relação detalhada de cada IP de origem utilizado na integração dos logs por campanha, indicando sua origem (`interno:perfil` ou `externo`) e volume total de consultas geradas. |
| **`ataques_manifesto.json`** | Manifesto com parâmetros da simulação, semente global (`SEED = 129547711`), distribuição de IPs por nível e hashes SHA-256. |
| **`separacao_manifesto.json`** | Telemetria detalhada do particionamento dos logs no processador AMD Ryzen 5 7600. |
| **`relatorio_coerencia_temporal.json`** | Auditoria formal comprovando contiguidade temporal estrita (Status: `VALIDADO_E_COERENTE`, 20.01h de margem inicial limpa e 4.56h pós-ataque). |
| **`benign_unique_ips.txt`** | Universo dos 25.000 IPs únicos gerados pela semente `129547711` na sub-rede `10.0.0.0/16`. |
