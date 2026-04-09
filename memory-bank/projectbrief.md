# Project Brief — TCC Call2Go

## Título do Trabalho
Desenvolvimento e Validação de um Sistema Automatizado para Detecção de Estratégias Call2Go em Vídeos do YouTube: Uma Análise de Confiabilidade Metodológica

## Objetivo Principal
Desenvolver e avaliar a confiabilidade de um sistema automatizado (baseado em regex) para detecção de estratégias Call2Go em descrições de vídeos do YouTube, utilizando validação cruzada entre classificação humana e automatizada como método de verificação.

**Foco real (orientador):** O TCC NÃO é sobre música nem rankings de artistas. É sobre METODOLOGIA — medir a confiabilidade de ferramentas automatizadas na análise de dados. Os artistas e vídeos são apenas o dataset.

## Hipóteses de Pesquisa
- **H0 (Nula):** O detector automatizado (regex) não apresenta concordância significativa com a classificação humana.
- **H1 (Alternativa):** O detector automatizado apresenta acurácia ≥ 85% em relação ao ground truth humano.
- **H2 (Secundária — YouTube):** Vídeos com Call2Go geram maior volume de visualizações.
- **H3 (Secundária — Cross-Platform):** O uso de Call2Go no YouTube impacta a popularidade no Spotify.

## Escopo
- **Amostra de artistas:** Extraída de playlists OFICIAIS do Spotify (Top 50 Brasil, Viral 50 Brasil) — fonte reprodutível e verificável
- **Volume:** ~50 vídeos mais recentes por artista
- **Método de detecção:** Regex sobre descrições dos vídeos
- **Validação:** Anotação manual humana (ground truth) + validação cruzada automatizada
- **Métricas de confiabilidade:** Acurácia, Precisão, Recall, F1-Score, Matriz de Confusão, Cohen's Kappa + Bootstrap IC 95%
- **Teste estatístico:** Mann-Whitney U (não paramétrico), α = 0.05

## Classificação Call2Go
| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| `link_direto` | Links Spotify na descrição | `https://open.spotify.com/...`, `spoti.fi/...` |
| `texto_implicito` | Menções textuais ao Spotify | "ouça no Spotify", "disponível no Spotify" |
| `nenhum` | Sem qualquer referência ao Spotify | — |

## Entregáveis Acadêmicos
- **Artefato principal:** Ferramenta reutilizável de validação cruzada (humano vs. máquina)
- Matriz de confusão demonstrando concordância
- Métricas de confiabilidade (Acurácia, Precisão, Recall, F1)
- Base de artistas com fonte oficial documentada e reprodutível
- Gráficos com DPI 300 (padrão banca)
- Testes estatísticos com nível de confiança de 95%
- Data Warehouse relacional (SQLite) documentado
- Pipeline ETL reprodutível com etapa de validação independente

## Pipeline Metodológico (com "volta")
```
1. Definir fonte oficial → Playlists Spotify (reprodutível)
2. Coletar dados → APIs YouTube + Spotify
3. Classificar automaticamente → Detector regex
4. Gerar amostra para validação → Seleção aleatória com seed
5. Anotar manualmente (humano) → Ground truth
6. VOLTA: Cruzar humano vs. máquina → Métricas de concordância
7. Interpretar discordâncias → Ajustar detector se necessário
8. Só então rodar análise estatística sobre dados validados
```
