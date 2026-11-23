# Camada 02: Dataset Refinado (Tabular CSV Compactado)

**Objetivo:** Diretório dos eventos estruturados em formato tabular (`label: 0/1`) gerados pelo parser `04_estruturar_logs_para_csv.py`.

> **Onde baixar o arquivo pronto:** Para pular o parsing dos logs brutos (~17,2 GB), baixe `dns_eventos_estruturados_48h.csv.gz` no Kaggle e coloque-o nesta pasta (`06_Datasets_e_Logs/02_dataset_refinado/`):  
> **https://www.kaggle.com/datasets/kaioguilherme/dns-nxdomain-flood-benign-48h**

---

## 1. Arquivos da Camada

| Arquivo | Tamanho | Registros | Status no Git |
| :--- | :---: | :---: | :--- |
| **`dns_eventos_estruturados_48h.csv.gz`** | 3,24 GB | `122.786.098` | Hospedado no Kaggle (não versionado no Git) |
| **`dns_eventos_estruturados_amostra.csv`** | ~11,6 MB | `100.000` | Gerado localmente na Etapa 2 (`--step 2`) |
| **`estruturacao_manifesto.json`** | 755 B | N/A | Versionado no repositório |

---

## 2. Dicionário de Colunas

```csv
datetime,timestamp_epoch,client_ip,client_port,client_ptr,domain,qtype,flags,resolver_ip,label
```

1. **`datetime`**: Timestamp no formato `DD-Mon-YYYY HH:MM:SS.mmm`.
2. **`timestamp_epoch`**: Época Unix contínua com resolução de milissegundos.
3. **`client_ip`**: Endereço IPv4 de origem da requisição.
4. **`client_port`**: Porta efêmera de transporte (`[49152, 65535]`).
5. **`client_ptr`**: Ponteiro hexadecimal do cliente BIND 9.
6. **`domain`**: FQDN consultado.
7. **`qtype`**: Tipo de registro DNS (`A`, `AAAA`, `MX`, `TXT`, etc.).
8. **`flags`**: Flags EDNS0 (`+E(0)`).
9. **`resolver_ip`**: IP do servidor recursivo (`192.168.0.10`).
10. **`label`**: Ground truth binário (`0` = tráfego benigno; `1` = ataque *NXDOMAIN Flood*).
