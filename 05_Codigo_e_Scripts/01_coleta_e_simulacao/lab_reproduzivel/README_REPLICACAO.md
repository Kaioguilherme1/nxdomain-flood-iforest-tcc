# Guia de Replicação do Laboratório Experimental (Testbed Docker)

Este documento fornece as instruções para subir o ambiente experimental isolado do TCC em qualquer máquina (Linux/macOS) com Docker Compose instalado.

---

## 1. Pré-requisitos

O `docker-compose.yml` referencia dois diretórios irmãos em `05_Codigo_e_Scripts/01_coleta_e_simulacao/`:

1. **`../dns-log-generator/`**: Clone o repositório irmão `dns-log-generator` dentro de `05_Codigo_e_Scripts/01_coleta_e_simulacao/dns-log-generator`:
   ```bash
   cd 05_Codigo_e_Scripts/01_coleta_e_simulacao
   git clone https://github.com/Kaioguilherme1/dns-log-generator.git
   ```
2. **`../nxdomain-script/domains.txt`**: Gere a lista de domínios DGA (*QakBot*) em `05_Codigo_e_Scripts/01_coleta_e_simulacao/nxdomain-script/domains.txt` utilizando a implementação de referência de [baderj/domain_generation_algorithms](https://github.com/baderj/domain_generation_algorithms) (um domínio por linha).

---

## 2. Topologia Virtual

- **Sub-rede isolada (`tcc_net`):** `192.168.2.0/24`
- **Servidor DNS (ISC BIND 9):** `192.168.2.200` (`bind9-dns`)
- **Cliente de Tráfego Benigno (`dns-log-generator`):** `192.168.2.202` (`client-benigno`)
- **Atacante NXDOMAIN Flood (`dnsperf` + DGA):** `192.168.2.203` (`attacker-nxdomain`)

---

## 3. Instruções de Execução

A partir desta pasta (`05_Codigo_e_Scripts/01_coleta_e_simulacao/lab_reproduzivel/`):

```bash
# 1. Iniciar o servidor BIND 9
docker compose up -d bind9-dns

# 2. Iniciar o gerador de consultas legítimas
docker compose up -d client-benigno

# 3. Disparar a campanha de testes de ataque
docker compose up attacker-nxdomain
```
