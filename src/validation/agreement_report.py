import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import os
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')


def generate_agreement_report(validation_file="data/validation/cross_validation_report.csv",
                              metrics_file="data/validation/cross_validation_report_metrics.json",
                              output_dir="data/plots"):
    """
    Gera visualizações da concordância entre classificação humana e automatizada.

    Artefatos gerados:
        1. Matriz de confusão (nível combinado) -- humano vs. detector vídeo+canal
        2. Gráfico de barras -- métricas por classe (nível combinado)
        3. Matriz de confusão (nível vídeo) -- humano vs. detector só no vídeo

    Esses gráficos são evidência direta da confiabilidade do detector
    e vão para o capítulo de Resultados do TCC.

    NOTA: Imagens limitadas a max 1800px em qualquer dimensão (figsize x dpi).
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

    # Detecta se usa formato novo (auto_combined_type) ou legado (auto_call2go_type)
    auto_col = 'auto_combined_type' if 'auto_combined_type' in df.columns else 'auto_call2go_type'

    # 1. Matriz de Confusão -- Nível Combinado (vídeo + canal)
    labels = ['nenhum', 'texto_implicito', 'link_direto']
    present_labels = [
        l for l in labels if l in df['manual_call2go_type'].values or l in df[auto_col].values]

    confusion = pd.crosstab(
        df['manual_call2go_type'],
        df[auto_col],
        rownames=['Humano (Ground Truth)'],
        colnames=['Detector Automatizado (Vídeo + Canal)']
    )

    # Reordena para manter consistência
    for l in present_labels:
        if l not in confusion.index:
            confusion.loc[l] = 0
        if l not in confusion.columns:
            confusion[l] = 0
    confusion = confusion.reindex(
        index=present_labels, columns=present_labels, fill_value=0)

    # figsize=(6,4) x dpi=300 = 1800x1200 px (seguro, < 2000px)
    plt.figure(figsize=(6, 4))
    sns.heatmap(confusion, annot=True, fmt='d', cmap='Blues',
                xticklabels=present_labels, yticklabels=present_labels,
                linewidths=0.5, linecolor='gray')
    plt.title("Matriz de Confusão: Humano vs. Detector (Vídeo + Canal)",
              fontsize=11, fontweight='bold')
    plt.ylabel("Classificação Humana", fontsize=10)
    plt.xlabel("Classificação Automatizada", fontsize=10)
    plt.tight_layout()

    cm_path = os.path.join(output_dir, "confusion_matrix_combined.png")
    plt.savefig(cm_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[OK] Matriz de confusão (combinado) salva em: {cm_path}")

    # 1b. Matriz de Confusão -- Nível Vídeo Apenas (se coluna existe)
    if 'auto_video_type' in df.columns:
        present_labels_v = [
            l for l in labels if l in df['manual_call2go_type'].values or l in df['auto_video_type'].values]

        confusion_v = pd.crosstab(
            df['manual_call2go_type'],
            df['auto_video_type'],
            rownames=['Humano (Ground Truth)'],
            colnames=['Detector Automatizado (Só Vídeo)']
        )
        for l in present_labels_v:
            if l not in confusion_v.index:
                confusion_v.loc[l] = 0
            if l not in confusion_v.columns:
                confusion_v[l] = 0
        confusion_v = confusion_v.reindex(
            index=present_labels_v, columns=present_labels_v, fill_value=0)

        plt.figure(figsize=(6, 4))
        sns.heatmap(confusion_v, annot=True, fmt='d', cmap='Oranges',
                    xticklabels=present_labels_v, yticklabels=present_labels_v,
                    linewidths=0.5, linecolor='gray')
        plt.title("Matriz de Confusão: Humano vs. Detector (Só Vídeo)",
                  fontsize=11, fontweight='bold')
        plt.ylabel("Classificação Humana", fontsize=10)
        plt.xlabel("Classificação Automatizada", fontsize=10)
        plt.tight_layout()

        cm_v_path = os.path.join(output_dir, "confusion_matrix_video_only.png")
        plt.savefig(cm_v_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"[OK] Matriz de confusão (só vídeo) salva em: {cm_v_path}")

    # 2. Métricas por classe (se o arquivo de métricas existir)
    if os.path.exists(metrics_file):
        with open(metrics_file, 'r', encoding='utf-8') as f:
            metrics_raw = json.load(f)

        # Suporta formato novo (com níveis) e legado (flat)
        if 'combined' in metrics_raw:
            metrics = metrics_raw['combined']
        else:
            metrics = metrics_raw

        if metrics:
            per_class = metrics.get('per_class', {})
            if per_class:
                classes = list(per_class.keys())
                precision_vals = [per_class[c]['precision'] for c in classes]
                recall_vals = [per_class[c]['recall'] for c in classes]
                f1_vals = [per_class[c]['f1_score'] for c in classes]

                x = np.arange(len(classes))
                width = 0.25

                # figsize=(6,4) x dpi=300 = 1800x1200 px (seguro)
                fig, ax = plt.subplots(figsize=(6, 4))
                bars1 = ax.bar(x - width, precision_vals, width,
                               label='Precisão', color='#2196F3')
                bars2 = ax.bar(x, recall_vals, width,
                               label='Recall', color='#FF9800')
                bars3 = ax.bar(x + width, f1_vals, width,
                               label='F1-Score', color='#4CAF50')

                ax.set_ylabel('Score', fontsize=10)
                ax.set_xlabel('Classe Call2Go', fontsize=10)
                ax.set_title('Métricas de Confiabilidade por Classe (Combinado)',
                             fontsize=11, fontweight='bold')
                ax.set_xticks(x)
                ax.set_xticklabels(classes, fontsize=9)
                ax.legend(fontsize=9)
                ax.set_ylim(0, 1.1)

                # Adiciona valores sobre as barras
                for bars in [bars1, bars2, bars3]:
                    for bar in bars:
                        height = bar.get_height()
                        if height > 0:
                            ax.annotate(f'{height:.0%}',
                                        xy=(bar.get_x() +
                                            bar.get_width() / 2, height),
                                        xytext=(0, 3), textcoords="offset points",
                                        ha='center', va='bottom', fontsize=8)

                plt.tight_layout()
                metrics_path = os.path.join(
                    output_dir, "validation_metrics_per_class.png")
                plt.savefig(metrics_path, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"[OK] Gráfico de métricas salvo em: {metrics_path}")

            # Resumo textual
            print(f"\n--- RESUMO PARA O TCC ---")
            acc = metrics.get('accuracy', 'N/A')
            kappa = metrics.get('cohens_kappa', 'N/A')
            kappa_ci = metrics.get('kappa_ci95', [])
            acc_ci = metrics.get('accuracy_ci95', [])
            kappa_interp = metrics.get('kappa_interpretation', '')

            print(f"Acuracia global (combinado): {acc}")
            if acc_ci:
                print(f"  IC95% Acuracia: [{acc_ci[0]}, {acc_ci[1]}]")
            if kappa != 'N/A':
                print(f"Cohen's Kappa (combinado): {kappa}")
                if kappa_ci:
                    print(f"  IC95% Kappa: [{kappa_ci[0]}, {kappa_ci[1]}]")
                if kappa_interp:
                    print(f"  Interpretacao (Landis & Koch): {kappa_interp}")
            print(f"Videos validados: {metrics.get('total_validated', 'N/A')}")
            print(f"Concordancias: {metrics.get('matches', 'N/A')}")
            print(f"Discordancias: {metrics.get('discordances', 'N/A')}")

            # Mostra métricas de vídeo-only e canal se disponíveis
            if 'video_only' in metrics_raw and metrics_raw['video_only']:
                vid_m = metrics_raw['video_only']
                vid_kappa = vid_m.get('cohens_kappa', 'N/A')
                vid_kappa_ci = vid_m.get('kappa_ci95', [])
                print(f"\nAcuracia (so video): {vid_m.get('accuracy', 'N/A')}")
                if vid_kappa != 'N/A':
                    print(f"Kappa (so video): {vid_kappa}")
                    if vid_kappa_ci:
                        print(
                            f"  IC95%: [{vid_kappa_ci[0]}, {vid_kappa_ci[1]}]")
            if 'channel_only' in metrics_raw and metrics_raw['channel_only']:
                ch_m = metrics_raw['channel_only']
                ch_kappa = ch_m.get('cohens_kappa', 'N/A')
                print(f"Acuracia (so canal): {ch_m.get('accuracy', 'N/A')}")
                if ch_kappa != 'N/A':
                    print(f"Kappa (so canal): {ch_kappa}")

    print(f"\n[OK] Relatório visual completo gerado em: {output_dir}/")


if __name__ == "__main__":
    generate_agreement_report()
