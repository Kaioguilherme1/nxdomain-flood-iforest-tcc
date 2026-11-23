# Camada 03: Dataset Final de Features (Gold / ML Feature Store)

**Objetivo:** Matriz de características agregadas por janela temporal ($\Delta t = 30\text{ s}$), pronta para treinamento e avaliação comparativa entre o Baseline de Nadler et al. (2019) e a Proposta do TCC.

---

## 1. Arquivos Contidos

| Arquivo | Registros | Descrição |
| :--- | :---: | :--- |
| **`dataset_features_48h_w30s.csv`** | 5.760 janelas | Matriz oficial de atributos janelada ($\Delta t = 30\text{ s}$) cobrindo 48h contínuas (2.400 janelas de treino nominal + 3.360 janelas de teste com 21 campanhas). |
| **`features_manifesto_w30s.json`** | N/A | Manifesto com parâmetros temporais e semente determinística (`SEED = 129547711`). |

---

## 2. Dicionário de Características (Features)

```csv
window_id,datetime,start_epoch,end_epoch,qps,max_consonant_streak,entropy,mean_fqdn_len,unique_ratio,total_queries,benign_queries,attack_queries,attack_ratio,label,nivel_ataque
```

| Atributo | Fórmula Matemática | Descrição | Modelo que Utiliza |
| :--- | :---: | :--- | :---: |
| **`qps`** | $\frac{N_{\text{total}}}{\Delta t}$ | Consultas por segundo na janela. | Nadler et al. / TCC Kaio |
| **`max_consonant_streak`** ($C_{\text{max}}$) | $\frac{1}{N} \sum \max_{s \in \mathcal{C}(d_i)} \|s\|$ | Média da maior sequência de consoantes consecutivas no subdomínio (Schüppen et al., 2018). | **Proposta TCC Kaio** |
| **`entropy`** ($H$) | $-\sum p_i \log_2(p_i)$ | Entropia de Shannon dos caracteres do primeiro label. | Nadler et al. / TCC Kaio |
| **`mean_fqdn_len`** ($\bar{L}$) | $\frac{1}{N} \sum \text{len}(\text{fqdn}_i)$ | Comprimento médio dos domínios consultados. | Nadler et al. / TCC Kaio |
| **`unique_ratio`** ($U$) | $\frac{\|D_{\text{únicos}}\|}{N_{\text{total}}}$ | Razão de domínios distintos consultados. | Nadler et al. / TCC Kaio |
| **`label`** | $\{0, 1\}$ | **0** = Janela Nominal / **1** = Janela com Ataque Ativo. | Ground Truth |

---

## 3. Configuração dos Experimentos de Comparação no TCC

1. **Baseline: Nadler et al. (2019):**
   * Features: `[qps, entropy, mean_fqdn_len, unique_ratio]` (4 dimensões estatísticas/léxicas sem dicionário).
   * Algoritmo: Isolation Forest ($n_{\text{estimators}} = 100$, calibração em tráfego nominal nas primeiras 20h).
2. **Proposta do TCC:**
   * Features: `[qps, max_consonant_streak, entropy, mean_fqdn_len, unique_ratio]` (5 dimensões com $C_{\text{max}}$).
   * Algoritmo: Isolation Forest nas mesmas condições de semente e particionamento.
