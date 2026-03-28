import os
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


def generate_agreement_report(validation_file="data/validation/cross_validation_report.csv",
                              metrics_file="data/validation/cross_validation_report_metrics.json",
                              output_dir="data/plots"):
    """
    Gera visualizações da concordância entre classificação humana e automatizada.

    Artefatos gerados:
        1. Matriz de confusão — mostra onde humano e máquina concordam/discordam
        2. Gráfico de barras — acurácia por classe

    Esses gráficos são evidência direta da confiabilidade do detector
    e vão para o capítulo de Resultados do TCC.
    """
    print("=" * 60)
    print("GERAÇÃO DE RELATÓRIO VISUAL DE CONCORDÂNCIA")
    print("=" * 60)

    if not os.path.exists(validation_file):
        print(f"[ERRO] Arquivo de validação não encontrado: {validation_file}")
        print("Execute primeiro: python -m src.validation.cross_validator")
        return

    df = pd.read_csv(validation_file)
    os.makedirs(output_dir, exist_ok=True)

    # 1. Matriz de Confusão
    labels = ['nenhum', 'texto_implicito', 'link_direto']
    present_labels = [
        l for l in labels if l in df['manual_call2go_type'].values or l in df['auto_call2go_type'].values]

    confusion = pd.crosstab(
        df['manual_call2go_type'],
        df['auto_call2go_type'],
        rownames=['Humano (Ground Truth)'],
        colnames=['Detector Automatizado']
    )

    # Reordena para manter consistência
    for l in present_labels:
        if l not in confusion.index:
            confusion.loc[l] = 0
        if l not in confusion.columns:
            confusion[l] = 0
    confusion = confusion.reindex(
        index=present_labels, columns=present_labels, fill_value=0)

    plt.figure(figsize=(8, 6))
    sns.heatmap(confusion, annot=True, fmt='d', cmap='Blues',
                xticklabels=present_labels, yticklabels=present_labels,
                linewidths=0.5, linecolor='gray')
    plt.title("Matriz de Confusão: Humano vs. Detector Automatizado",
              fontsize=13, fontweight='bold')
    plt.ylabel("Classificação Humana (Ground Truth)", fontsize=11)
    plt.xlabel("Classificação Automatizada (Regex)", fontsize=11)
    plt.tight_layout()

    cm_path = os.path.join(output_dir, "confusion_matrix_validation.png")
    plt.savefig(cm_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Matriz de confusão salva em: {cm_path}")

    # 2. Métricas por classe (se o arquivo de métricas existir)
    if os.path.exists(metrics_file):
        with open(metrics_file, 'r', encoding='utf-8') as f:
            metrics = json.load(f)

        per_class = metrics.get('per_class', {})
        if per_class:
            classes = list(per_class.keys())
            precision_vals = [per_class[c]['precision'] for c in classes]
            recall_vals = [per_class[c]['recall'] for c in classes]
            f1_vals = [per_class[c]['f1_score'] for c in classes]

            x = np.arange(len(classes))
            width = 0.25

            fig, ax = plt.subplots(figsize=(10, 6))
            bars1 = ax.bar(x - width, precision_vals, width,
                           label='Precisão', color='#2196F3')
            bars2 = ax.bar(x, recall_vals, width,
                           label='Recall', color='#FF9800')
            bars3 = ax.bar(x + width, f1_vals, width,
                           label='F1-Score', color='#4CAF50')

            ax.set_ylabel('Score', fontsize=12)
            ax.set_xlabel('Classe Call2Go', fontsize=12)
            ax.set_title('Métricas de Confiabilidade do Detector por Classe',
                         fontsize=13, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(classes)
            ax.legend()
            ax.set_ylim(0, 1.1)

            # Adiciona valores sobre as barras
            for bars in [bars1, bars2, bars3]:
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.annotate(f'{height:.0%}',
                                    xy=(bar.get_x() + bar.get_width() / 2, height),
                                    xytext=(0, 3), textcoords="offset points",
                                    ha='center', va='bottom', fontsize=9)

            plt.tight_layout()
            metrics_path = os.path.join(
                output_dir, "validation_metrics_per_class.png")
            plt.savefig(metrics_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Gráfico de métricas salvo em: {metrics_path}")

            # Resumo textual
            print(f"\n--- RESUMO PARA O TCC ---")
            print(f"Acurácia global: {metrics['accuracy']:.1%}")
            print(f"Vídeos validados: {metrics['total_validated']}")
            print(f"Concordâncias: {metrics['matches']}")
            print(f"Discordâncias: {metrics['discordances']}")

    print(f"\n✅ Relatório visual completo gerado em: {output_dir}/")


if __name__ == "__main__":
    generate_agreement_report()
