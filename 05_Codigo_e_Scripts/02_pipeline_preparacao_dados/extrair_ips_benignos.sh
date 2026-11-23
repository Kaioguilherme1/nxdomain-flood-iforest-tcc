#!/bin/sh
# Extrai os IPs de origem unicos do log benigno (somente linhas "client @").
# Usado para verificar que o pool reconstruido por unificar_logs_ataques_reprodutivel.py
# e identico ao conjunto de usuarios efetivamente presentes no log do gerador.
# Uso: sh extrair_ips_benignos.sh <dns_events.log> <saida.txt>
LC_ALL=C awk '/ client @/ { split($5, a, "#"); print a[1] }' "$1" | LC_ALL=C sort -u > "$2"
echo "ips_unicos=$(wc -l < "$2")"
