#!/usr/bin/env python3
"""
Campanha probabilística de ataques NXDOMAIN Flood com dnsperf.

O programa executa uma campanha experimental de 24 horas composta por
ataques leves, moderados e intensos, distribuídos ao longo do período.

Uso exclusivo em ambiente controlado e autorizado.

Arquivo de entrada:
    domains.txt

Formato esperado:
    um domínio por linha

Exemplo:
    dominioinexistente1.com
    dominioinexistente2.net

O script converte automaticamente a entrada para o formato:

    dominioinexistente1.com A
    dominioinexistente2.net A
"""

from __future__ import annotations

import ipaddress
import json
import random
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURAÇÕES GERAIS
# ============================================================

# Servidor DNS autoritativo do laboratório.
DESTINO_DNS = "192.168.2.200"

# Porta do serviço DNS.
PORTA_DNS = 53

# Rede autorizada para execução.
# O script bloqueará destinos fora dessa rede.
REDE_AUTORIZADA = "192.168.2.0/24"

# Arquivo com um domínio por linha.
ARQUIVO_DOMINIOS = Path("domains.txt")

# Diretório de saída.
DIRETORIO_SAIDA = Path("campanha_nxdomain")

# Executável do dnsperf.
EXECUTAVEL_DNSPERF = "dnsperf"

# Fuso horário do experimento.
FUSO_HORARIO = "America/Boa_Vista"

# Duração total da campanha.
DURACAO_CAMPANHA_HORAS = 24

# Quantidade de eventos de ataque.
QUANTIDADE_EVENTOS = 21

# Tempo até o início da campanha.
ATRASO_INICIAL_MINUTOS = 5

# Intervalos sem ataque entre os eventos.
INTERVALO_MINIMO_MINUTOS = 10
INTERVALO_MAXIMO_MINUTOS = 60

# Semente pseudoaleatória.
# Mantendo o mesmo valor, a distribuição será reproduzível.
SEED_ALEATORIA = 20260607

# Confirmação antes de iniciar a execução.
EXIGIR_CONFIRMACAO = True


# ============================================================
# CONFIGURAÇÕES DOS ATAQUES
# ============================================================
#
# LEVE:
# dnsperf -s 192.168.2.200 -d domains.txt
#         -l 600 -c 10 -Q 1000 -t 2
#
# MODERADO:
# dnsperf -s 192.168.2.200 -d domains.txt
#         -l 900 -c 40 -Q 5000 -t 2
#
# INTENSO:
# dnsperf -s 192.168.2.200 -d domains.txt
#         -l 1800 -c 100 -Q 20000 -t 2

TIPOS_ATAQUE = {
    "LEVE": {
        "probabilidade": 11,
        "duracao_segundos": 600,
        "clientes": 10,
        "qps": 1000,
        "timeout": 2,
    },
    "MODERADO": {
        "probabilidade": 6,
        "duracao_segundos": 900,
        "clientes": 40,
        "qps": 5000,
        "timeout": 2,
    },
    "INTENSO": {
        "probabilidade": 4,
        "duracao_segundos": 1800,
        "clientes": 100,
        "qps": 20000,
        "timeout": 2,
    },
}


# ============================================================
# VARIÁVEIS INTERNAS
# ============================================================

FUSO = ZoneInfo(FUSO_HORARIO)
ENCERRAMENTO_SOLICITADO = False


@dataclass
class EventoAtaque:
    id: int
    categoria: str
    agendado_para: str
    duracao_segundos: int
    clientes: int
    qps_configurado: int
    timeout_segundos: int
    arquivo_log: str
    status: str = "PENDENTE"
    iniciado_em: str | None = None
    finalizado_em: str | None = None
    codigo_retorno: int | None = None


# ============================================================
# FUNÇÕES DE DATA E CONTROLE
# ============================================================

def agora() -> datetime:
    return datetime.now(FUSO)


def converter_data(valor: str) -> datetime:
    data = datetime.fromisoformat(valor)

    if data.tzinfo is None:
        data = data.replace(tzinfo=FUSO)

    return data.astimezone(FUSO)


def tratar_sinal(numero: int, frame: object) -> None:
    del numero, frame

    global ENCERRAMENTO_SOLICITADO
    ENCERRAMENTO_SOLICITADO = True

    print(
        "\nInterrupção solicitada. Encerrando o evento atual com segurança.",
        flush=True,
    )


# ============================================================
# VALIDAÇÕES
# ============================================================

def validar_destino() -> None:
    try:
        destino = ipaddress.ip_address(DESTINO_DNS)
        rede = ipaddress.ip_network(REDE_AUTORIZADA)
    except ValueError as erro:
        raise RuntimeError(
            "DESTINO_DNS ou REDE_AUTORIZADA possui valor inválido."
        ) from erro

    if destino.version != 4:
        raise RuntimeError("O destino deve ser um endereço IPv4.")

    if destino not in rede:
        raise RuntimeError(
            f"Destino bloqueado: {destino} não pertence à rede "
            f"autorizada {rede}."
        )

    if not destino.is_private:
        raise RuntimeError(
            "O destino deve pertencer a uma rede IPv4 privada."
        )


def validar_ambiente() -> None:
    validar_destino()

    if not ARQUIVO_DOMINIOS.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {ARQUIVO_DOMINIOS.resolve()}"
        )

    if ARQUIVO_DOMINIOS.stat().st_size == 0:
        raise RuntimeError(
            f"O arquivo {ARQUIVO_DOMINIOS} está vazio."
        )

    if shutil.which(EXECUTAVEL_DNSPERF) is None:
        raise RuntimeError(
            f"O executável '{EXECUTAVEL_DNSPERF}' não foi encontrado no PATH."
        )

    if DURACAO_CAMPANHA_HORAS <= 0:
        raise RuntimeError(
            "DURACAO_CAMPANHA_HORAS deve ser maior que zero."
        )

    if QUANTIDADE_EVENTOS <= 0:
        raise RuntimeError(
            "QUANTIDADE_EVENTOS deve ser maior que zero."
        )

    if INTERVALO_MINIMO_MINUTOS < 0:
        raise RuntimeError(
            "INTERVALO_MINIMO_MINUTOS não pode ser negativo."
        )

    if INTERVALO_MAXIMO_MINUTOS < INTERVALO_MINIMO_MINUTOS:
        raise RuntimeError(
            "INTERVALO_MAXIMO_MINUTOS deve ser maior ou igual ao mínimo."
        )


# ============================================================
# PREPARAÇÃO DO ARQUIVO DE DOMÍNIOS
# ============================================================

def preparar_arquivo_dnsperf(destino: Path) -> int:
    """
    Converte um arquivo com um domínio por linha para o formato:

        dominio.com A
    """

    quantidade = 0

    with (
        ARQUIVO_DOMINIOS.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as entrada,
        destino.open(
            "w",
            encoding="utf-8",
        ) as saida,
    ):
        for numero_linha, linha in enumerate(entrada, start=1):
            valor = linha.strip()

            if not valor or valor.startswith("#"):
                continue

            # Também aceita arquivos que já contenham "dominio A".
            dominio = valor.split()[0].lower().rstrip(".")

            if "." not in dominio:
                print(
                    f"Aviso: linha {numero_linha} ignorada: {dominio}",
                    file=sys.stderr,
                )
                continue

            saida.write(f"{dominio} A\n")
            quantidade += 1

    if quantidade == 0:
        raise RuntimeError(
            "Nenhum domínio válido foi encontrado no arquivo de entrada."
        )

    return quantidade


# ============================================================
# MODELO PROBABILÍSTICO
# ============================================================

def escolher_categoria(
        gerador: random.Random,
        categoria_anterior: str | None,
        horas_desde_intenso: float,
) -> str:
    """
    Seleciona a categoria do próximo ataque com base nas probabilidades
    configuradas e no contexto dos eventos anteriores.
    """

    pesos = {
        categoria: configuracao["probabilidade"]
        for categoria, configuracao in TIPOS_ATAQUE.items()
    }

    # Evita ataques intensos consecutivos.
    if categoria_anterior == "INTENSO":
        pesos["INTENSO"] *= 0.10
        pesos["LEVE"] *= 1.50

    # Após ataque moderado, aumenta a chance de ataque leve.
    elif categoria_anterior == "MODERADO":
        pesos["LEVE"] *= 1.25
        pesos["INTENSO"] *= 0.70

    # Ajusta a chance de ataque intenso conforme o tempo transcorrido.
    if horas_desde_intenso >= 6:
        pesos["INTENSO"] *= 2.50
    elif horas_desde_intenso >= 4:
        pesos["INTENSO"] *= 1.50
    elif horas_desde_intenso < 2:
        pesos["INTENSO"] *= 0.25

    categorias = list(pesos.keys())
    valores = list(pesos.values())

    return gerador.choices(
        categorias,
        weights=valores,
        k=1,
    )[0]


def escolher_intervalo(
        gerador: random.Random,
        categoria: str,
) -> int:
    """
    Define o intervalo sem ataque após cada evento.
    """

    if categoria == "INTENSO":
        minimo = max(
            INTERVALO_MINIMO_MINUTOS,
            25,
        )

        return gerador.randint(
            minimo,
            INTERVALO_MAXIMO_MINUTOS,
        )

    if categoria == "MODERADO":
        minimo = max(
            INTERVALO_MINIMO_MINUTOS,
            15,
        )

        return gerador.randint(
            minimo,
            INTERVALO_MAXIMO_MINUTOS,
        )

    return gerador.randint(
        INTERVALO_MINIMO_MINUTOS,
        INTERVALO_MAXIMO_MINUTOS,
    )


def gerar_agenda(
        inicio: datetime,
        diretorio_logs: Path,
) -> list[EventoAtaque]:
    gerador = random.Random(SEED_ALEATORIA)

    fim_campanha = inicio + timedelta(
        hours=DURACAO_CAMPANHA_HORAS
    )

    eventos: list[EventoAtaque] = []

    cursor = inicio
    categoria_anterior: str | None = None
    ultimo_intenso: datetime | None = None

    while len(eventos) < QUANTIDADE_EVENTOS:
        if ultimo_intenso is None:
            horas_desde_intenso = 99.0
        else:
            horas_desde_intenso = (
                                          cursor - ultimo_intenso
                                  ).total_seconds() / 3600

        categoria = escolher_categoria(
            gerador=gerador,
            categoria_anterior=categoria_anterior,
            horas_desde_intenso=horas_desde_intenso,
        )

        configuracao = TIPOS_ATAQUE[categoria]

        # Evita início sempre em minutos exatos.
        variacao_minutos = gerador.randint(0, 9)

        inicio_evento = cursor + timedelta(
            minutes=variacao_minutos
        )

        fim_evento = inicio_evento + timedelta(
            seconds=configuracao["duracao_segundos"]
        )

        if fim_evento > fim_campanha:
            break

        nome_log = (
            f"ataque_nxdomain_"
            f"{inicio_evento.strftime('%Y%m%d_%H%M')}_"
            f"{categoria}.txt"
        )

        evento = EventoAtaque(
            id=len(eventos) + 1,
            categoria=categoria,
            agendado_para=inicio_evento.isoformat(),
            duracao_segundos=configuracao["duracao_segundos"],
            clientes=configuracao["clientes"],
            qps_configurado=configuracao["qps"],
            timeout_segundos=configuracao["timeout"],
            arquivo_log=str(
                diretorio_logs / nome_log
            ),
        )

        eventos.append(evento)

        if categoria == "INTENSO":
            ultimo_intenso = inicio_evento

        categoria_anterior = categoria

        intervalo = escolher_intervalo(
            gerador=gerador,
            categoria=categoria,
        )

        cursor = fim_evento + timedelta(
            minutes=intervalo
        )

    return eventos


# ============================================================
# MANIFESTO E EXIBIÇÃO
# ============================================================

def salvar_manifesto(
        caminho: Path,
        eventos: list[EventoAtaque],
        metadados: dict,
) -> None:
    temporario = caminho.with_suffix(".tmp")

    conteudo = {
        "metadados": metadados,
        "configuracoes_ataques": TIPOS_ATAQUE,
        "eventos": [
            asdict(evento)
            for evento in eventos
        ],
    }

    with temporario.open(
            "w",
            encoding="utf-8",
    ) as arquivo:
        json.dump(
            conteudo,
            arquivo,
            indent=2,
            ensure_ascii=False,
        )

    temporario.replace(caminho)


def mostrar_agenda(
        eventos: list[EventoAtaque],
) -> None:
    print()
    print(
        f"{'ID':<4} "
        f"{'DATA/HORA':<18} "
        f"{'TIPO':<10} "
        f"{'DURAÇÃO':>8} "
        f"{'CLIENTES':>9} "
        f"{'QPS':>8}"
    )
    print("-" * 67)

    for evento in eventos:
        data = converter_data(
            evento.agendado_para
        )

        print(
            f"{evento.id:<4} "
            f"{data.strftime('%d/%m/%Y %H:%M'):<18} "
            f"{evento.categoria:<10} "
            f"{evento.duracao_segundos:>7}s "
            f"{evento.clientes:>9} "
            f"{evento.qps_configurado:>8}"
        )

    print()

    for categoria in TIPOS_ATAQUE:
        quantidade = sum(
            evento.categoria == categoria
            for evento in eventos
        )

        print(
            f"{categoria}: {quantidade} evento(s)"
        )


# ============================================================
# EXECUÇÃO DO DNSPERF
# ============================================================

def montar_comando(
        evento: EventoAtaque,
        arquivo_dnsperf: Path,
) -> list[str]:
    return [
        EXECUTAVEL_DNSPERF,
        "-s",
        DESTINO_DNS,
        "-p",
        str(PORTA_DNS),
        "-d",
        str(arquivo_dnsperf),
        "-l",
        str(evento.duracao_segundos),
        "-c",
        str(evento.clientes),
        "-Q",
        str(evento.qps_configurado),
        "-t",
        str(evento.timeout_segundos),
    ]


def esperar_ate(
        instante: datetime,
) -> bool:
    while not ENCERRAMENTO_SOLICITADO:
        restante = (
                instante - agora()
        ).total_seconds()

        if restante <= 0:
            return True

        if restante > 300:
            tempo_espera = 60
        elif restante > 60:
            tempo_espera = 10
        else:
            tempo_espera = 1

        time.sleep(tempo_espera)

    return False


def executar_evento(
        evento: EventoAtaque,
        arquivo_dnsperf: Path,
) -> int:
    comando = montar_comando(
        evento=evento,
        arquivo_dnsperf=arquivo_dnsperf,
    )

    caminho_log = Path(
        evento.arquivo_log
    )

    caminho_log.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    evento.status = "EXECUTANDO"
    evento.iniciado_em = agora().isoformat()

    print()
    print(
        f"Iniciando ataque {evento.categoria}: "
        f"{evento.qps_configurado} QPS, "
        f"{evento.clientes} clientes, "
        f"{evento.duracao_segundos} segundos."
    )

    print(
        "Comando:",
        " ".join(comando),
    )

    with caminho_log.open(
            "w",
            encoding="utf-8",
    ) as log:
        log.write(
            "# Experimento controlado de NXDOMAIN Flood\n"
        )

        log.write(
            f"# Evento: {evento.id}\n"
        )

        log.write(
            f"# Categoria: {evento.categoria}\n"
        )

        log.write(
            f"# Agendado para: {evento.agendado_para}\n"
        )

        log.write(
            f"# Início real: {evento.iniciado_em}\n"
        )

        log.write(
            f"# Destino: {DESTINO_DNS}:{PORTA_DNS}\n"
        )

        log.write(
            f"# Comando: {' '.join(comando)}\n\n"
        )

        log.flush()

        processo = subprocess.Popen(
            comando,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )

        while processo.poll() is None:
            if ENCERRAMENTO_SOLICITADO:
                processo.terminate()

                try:
                    processo.wait(
                        timeout=10
                    )
                except subprocess.TimeoutExpired:
                    processo.kill()
                    processo.wait()

                return 130

            time.sleep(1)

    return processo.returncode


def executar_campanha(
        eventos: list[EventoAtaque],
        arquivo_dnsperf: Path,
        manifesto: Path,
        metadados: dict,
) -> None:
    for evento in eventos:
        if ENCERRAMENTO_SOLICITADO:
            break

        horario = converter_data(
            evento.agendado_para
        )

        print()
        print(
            f"Próximo evento: {evento.categoria} em "
            f"{horario.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        if not esperar_ate(horario):
            break

        codigo = executar_evento(
            evento=evento,
            arquivo_dnsperf=arquivo_dnsperf,
        )

        evento.codigo_retorno = codigo
        evento.finalizado_em = agora().isoformat()

        if codigo == 0:
            evento.status = "CONCLUIDO"
        elif codigo == 130:
            evento.status = "INTERROMPIDO"
        else:
            evento.status = "FALHOU"

        salvar_manifesto(
            caminho=manifesto,
            eventos=eventos,
            metadados=metadados,
        )

        print(
            f"Evento {evento.id} encerrado: "
            f"{evento.status}."
        )


# ============================================================
# CONFIRMAÇÃO
# ============================================================

def confirmar_execucao(
        eventos: list[EventoAtaque],
) -> None:
    if not EXIGIR_CONFIRMACAO:
        return

    print()
    print("=" * 65)
    print("CONFIRMAÇÃO DA CAMPANHA")
    print("=" * 65)

    print(
        f"Destino: {DESTINO_DNS}:{PORTA_DNS}"
    )

    print(
        f"Rede autorizada: {REDE_AUTORIZADA}"
    )

    print(
        f"Quantidade de eventos: {len(eventos)}"
    )

    print(
        f"Duração da campanha: {DURACAO_CAMPANHA_HORAS} horas"
    )

    resposta = input(
        '\nDigite "EXECUTAR" para iniciar a campanha: '
    ).strip()

    if resposta != "EXECUTAR":
        raise RuntimeError(
            "Execução cancelada pelo usuário."
        )


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def main() -> int:
    validar_ambiente()

    DIRETORIO_SAIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    diretorio_logs = (
            DIRETORIO_SAIDA / "eventos"
    )

    diretorio_logs.mkdir(
        parents=True,
        exist_ok=True,
    )

    arquivo_dnsperf = (
            DIRETORIO_SAIDA / "domains_dnsperf.txt"
    )

    manifesto = (
            DIRETORIO_SAIDA / "manifesto.json"
    )

    quantidade_dominios = preparar_arquivo_dnsperf(
        destino=arquivo_dnsperf
    )

    inicio_campanha = (
            agora()
            + timedelta(
        minutes=ATRASO_INICIAL_MINUTOS
    )
    ).replace(
        second=0,
        microsecond=0,
    )

    eventos = gerar_agenda(
        inicio=inicio_campanha,
        diretorio_logs=diretorio_logs,
    )

    if not eventos:
        raise RuntimeError(
            "Nenhum evento foi gerado."
        )

    if len(eventos) < QUANTIDADE_EVENTOS:
        print(
            f"Aviso: foram gerados {len(eventos)} eventos, "
            f"embora {QUANTIDADE_EVENTOS} tenham sido solicitados.",
            file=sys.stderr,
        )

    metadados = {
        "criado_em": agora().isoformat(),
        "inicio_campanha": inicio_campanha.isoformat(),
        "fim_campanha": (
                inicio_campanha
                + timedelta(
            hours=DURACAO_CAMPANHA_HORAS
        )
        ).isoformat(),
        "duracao_campanha_horas": DURACAO_CAMPANHA_HORAS,
        "quantidade_eventos_planejada": QUANTIDADE_EVENTOS,
        "quantidade_eventos_gerada": len(eventos),
        "destino_dns": DESTINO_DNS,
        "porta_dns": PORTA_DNS,
        "rede_autorizada": REDE_AUTORIZADA,
        "arquivo_original": str(
            ARQUIVO_DOMINIOS.resolve()
        ),
        "arquivo_dnsperf": str(
            arquivo_dnsperf.resolve()
        ),
        "quantidade_dominios": quantidade_dominios,
        "seed": SEED_ALEATORIA,
        "intervalo_minimo_minutos": INTERVALO_MINIMO_MINUTOS,
        "intervalo_maximo_minutos": INTERVALO_MAXIMO_MINUTOS,
    }

    salvar_manifesto(
        caminho=manifesto,
        eventos=eventos,
        metadados=metadados,
    )

    mostrar_agenda(
        eventos=eventos
    )

    print()
    print(
        f"Domínios preparados: {quantidade_dominios}"
    )

    print(
        f"Arquivo dnsperf: {arquivo_dnsperf.resolve()}"
    )

    print(
        f"Manifesto: {manifesto.resolve()}"
    )

    print(
        f"Destino: {DESTINO_DNS}:{PORTA_DNS}"
    )

    confirmar_execucao(
        eventos=eventos
    )

    executar_campanha(
        eventos=eventos,
        arquivo_dnsperf=arquivo_dnsperf,
        manifesto=manifesto,
        metadados=metadados,
    )

    print()
    print("Campanha encerrada.")

    return 0


if __name__ == "__main__":
    signal.signal(
        signal.SIGINT,
        tratar_sinal,
    )

    signal.signal(
        signal.SIGTERM,
        tratar_sinal,
    )

    try:
        raise SystemExit(
            main()
        )

    except (
            RuntimeError,
            FileNotFoundError,
    ) as erro:
        print(
            f"Erro: {erro}",
            file=sys.stderr,
        )

        raise SystemExit(1)