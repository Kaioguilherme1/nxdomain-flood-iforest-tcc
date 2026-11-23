# Camada 01: Dataset Bruto (Logs ISC BIND 9)

**Objetivo:** Diretório de destino para os logs brutos em texto claro gerados pelo resolvedor ISC BIND 9.

> **Onde baixar os arquivos:** Os arquivos desta camada excedem o limite do GitHub e estão hospedados publicamente no Kaggle:  
> **https://www.kaggle.com/datasets/kaioguilherme/dns-nxdomain-flood-benign-48h**

---

## 1. Arquivos Esperados Nesta Pasta

Após baixar o pacote do Kaggle (`01_logs_brutos/`), coloque os dois arquivos abaixo diretamente neste diretório (`06_Datasets_e_Logs/01_dataset_bruto/`):

| Arquivo | Volume no Kaggle | Descrição |
| :--- | :---: | :--- |
| **`benigno_unificado.log`** | 11,94 GB (89.174.860 consultas) | Tráfego legítimo de 25.000 usuários (`10.0.0.0/16`, `SEED = 129547711`) cobrindo 48h contínuas (`07-Jun-2026` a `08-Jun-2026`). |
| **`ataques_unificados.log`** | 5,27 GB (37.176.870 consultas) | Captura bruta das 21 campanhas *NXDOMAIN Flood* (DGA *QakBot*) com IPs normalizados deterministicamente (60% internos / 40% externos). |

*(Alternativamente, você pode gerar o tráfego benigno do zero com o repositório irmão [dns-log-generator](https://github.com/Kaioguilherme1/dns-log-generator).)*

---

## 2. Formato Técnico BIND 9

Ambos os arquivos seguem a sintaxe nativa de `query logging`:

```text
DD-Mon-YYYY HH:MM:SS.mmm client @0x<ptr> <ip>#<porta> (<fqdn>): query: <fqdn> IN <tipo> +E(0) (<ip_resolvedor>)
```

* **Resolvedor Normalizado:** `192.168.0.10`
* **Flags EDNS0:** `+E(0)`
* **Portas Efêmeras:** $[49152, 65535]$
