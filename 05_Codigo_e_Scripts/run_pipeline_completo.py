#!/usr/bin/env python3
"""
Orquestrador de execucao do pipeline de preparacao de dados, extracao de atributos,
treinamento dos modelos Isolation Forest e geracao de figuras/relatorios do TCC.
"""

import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conf


def check_status():
    layers = [
        ("01_dataset_bruto (opcional via Kaggle/gerador)", [
            conf.BENIGN_LOG_PATH,
            conf.ATTACK_LOG_PATH,
        ]),
        ("02_dataset_refinado (opcional via Kaggle/step 2)", [
            conf.STRUCTURED_CSV_GZ,
            conf.STRUCTURED_SAMPLE_CSV,
        ]),
        ("03_dataset_final_features (incluso no repo)", [
            conf.DATASET_OFFICIAL_PATH,
        ]),
        ("04_metadados_ground_truth", [
            conf.CAMPAIGNS_CSV_PATH,
            os.path.join(conf.METADATA_DIR, "relatorio_coerencia_temporal.json"),
        ]),
        ("05_resultados_e_relatorios", [
            os.path.join(conf.RESULTS_TABLES_DIR, "tabela_01_resumo_comparativo_modelos.csv"),
            os.path.join(conf.FINAL_TCC_ARTIFACTS_DIR, "Tabela_3_campanhas_ataque.csv"),
            os.path.join(conf.FINAL_TCC_ARTIFACTS_DIR, "Tabela_4_desempenho_global.csv"),
            os.path.join(conf.FINAL_TCC_ARTIFACTS_DIR, "Tabela_5_atributos_por_intensidade.csv"),
            os.path.join(conf.FINAL_TCC_ARTIFACTS_DIR, "Figura_1_mecanismo_isolamento.png"),
            os.path.join(conf.FINAL_TCC_ARTIFACTS_DIR, "Figura_2_matrizes_confusao.png"),
            os.path.join(conf.FINAL_TCC_ARTIFACTS_DIR, "Figura_3_recall_por_intensidade.png"),
            os.path.join(conf.FINAL_TCC_ARTIFACTS_DIR, "Figura_4_diluicao_diurna_ataque_leve.png"),
        ]),
    ]

    for name, files in layers:
        print(f"\n[{name}]")
        for f in files:
            if os.path.exists(f):
                size = os.path.getsize(f)
                if size > 1e9:
                    s_str = f"{size / 1e9:.2f} GB"
                elif size > 1e6:
                    s_str = f"{size / 1e6:.2f} MB"
                else:
                    s_str = f"{size / 1e3:.1f} KB"
                print(f"  OK      {os.path.basename(f):44s} ({s_str})")
            else:
                print(f"  MISSING {os.path.basename(f):44s}")


def run_step_1():
    script = os.path.join(conf.SCRIPTS_DIR, "02_pipeline_preparacao_dados", "03_validar_coerencia_temporal.py")
    subprocess.run([sys.executable, script], check=True)


def run_step_2():
    script = os.path.join(conf.SCRIPTS_DIR, "02_pipeline_preparacao_dados", "04_estruturar_logs_para_csv.py")
    subprocess.run([sys.executable, script], check=True)


def run_step_3(window_sec=conf.WINDOW_SIZE_SEC):
    script = os.path.join(conf.SCRIPTS_DIR, "03_engenharia_de_features", "extrair_features_janeladas.py")
    subprocess.run([sys.executable, script, "--window-sec", str(window_sec)], check=True)


def run_tcc_artifacts():
    script_tcc = os.path.join(conf.SCRIPTS_DIR, "04_treinamento_ia_e_avaliacao", "gerar_artefatos_tcc_simplificado.py")
    subprocess.run([conf.PYTHON_ML_BIN, script_tcc], check=True)


def run_step_4():
    script_train = os.path.join(conf.SCRIPTS_DIR, "04_treinamento_ia_e_avaliacao", "01_treinar_e_comparar_modelos.py")
    subprocess.run([conf.PYTHON_ML_BIN, script_train], check=True)

    script_plots = os.path.join(conf.SCRIPTS_DIR, "04_treinamento_ia_e_avaliacao", "02_gerar_graficos_e_tabelas.py")
    subprocess.run([conf.PYTHON_ML_BIN, script_plots], check=True)

    run_tcc_artifacts()


def run_step_5():
    script = os.path.join(conf.SCRIPTS_DIR, "05_relatorios_e_visualizacao", "compilar_relatorio_html.py")
    subprocess.run([sys.executable, script], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="Verifica a presenca dos arquivos de dados e resultados")
    parser.add_argument("--tcc", action="store_true", help="Gera rapidamente as 4 figuras e 3 tabelas exatas do texto final do TCC")
    parser.add_argument("--all", action="store_true", help="Executa todas as etapas do pipeline (requer logs brutos)")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4, 5], help="Executa uma etapa especifica (1 a 5)")
    parser.add_argument("--window-sec", type=int, default=conf.WINDOW_SIZE_SEC, help="Duracao da janela em segundos")
    args = parser.parse_args()

    if args.status or len(sys.argv) == 1:
        check_status()
        return

    t0 = time.time()
    if args.tcc:
        run_tcc_artifacts()
    elif args.all:
        run_step_1()
        run_step_2()
        run_step_3(args.window_sec)
        run_step_4()
        run_step_5()
    elif args.step == 1:
        run_step_1()
    elif args.step == 2:
        run_step_2()
    elif args.step == 3:
        run_step_3(args.window_sec)
    elif args.step == 4:
        run_step_4()
    elif args.step == 5:
        run_step_5()

    print(f"\nExecucao finalizada em {time.time() - t0:.1f}s.")


if __name__ == "__main__":
    main()
