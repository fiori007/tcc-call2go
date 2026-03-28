# Progress — TCC Call2Go

## Histórico de Marcos

### ✅ Concluído
- **Coleta Spotify** — Script funcional, dados coletados em 12/03/2026 para 6 artistas
- **Coleta YouTube** — Script funcional com resolução dinâmica de canal, ~50 vídeos/artista coletados
- **Detector Call2Go** — Motor NLP via regex implementado, classifica em `link_direto`, `texto_implicito`, `nenhum`
- **Data Warehouse** — SQLite com schema estrela (dim_artist, fact_yt_videos, fact_spotify_metrics)
- **EDA** — Boxplot de distribuição de views por tipo de Call2Go (escala log)
- **Teste de Hipótese** — Mann-Whitney U testando H1 (views YouTube)
- **Análise Cross-Platform** — Scatter plot views × popularity + teste Mann-Whitney para H2
- **Memory Bank** — Estrutura de contexto persistente criada (28/03/2026)

### 🔲 Pendente / Ideias Futuras
- Expandir amostra para mais artistas ou gêneros musicais
- Coleta longitudinal do Spotify (múltiplas datas para série temporal real)
- Notebooks Jupyter para apresentação interativa dos resultados
- Teste de correlação Spearman (views × popularity)
- Descomentar e fixar dependências no `requirements.txt` (matplotlib, seaborn, scipy)
- Análise de engagement rate (likes/views, comments/views) por tipo de Call2Go
- Documentação formal de limitações e vieses para o texto do TCC
- Possível expansão do detector para capturar padrões adicionais (Deezer, Apple Music)

## Dados Coletados (Snapshot)
| Artista | Spotify Followers | Spotify Pop | Vídeos YouTube |
|---------|-------------------|-------------|----------------|
| Anitta | 18.6M | 79 | ~50 |
| Marília Mendonça | 39.5M | 77 | ~50 |
| Henrique e Juliano | 32.3M | 84 | ~50 |
| Luan Santana | — | — | ~50 |
| Zé Neto e Cristiano | — | — | ~50 |
| Gusttavo Lima | 10.2M | 80 | ~50 |

## Observações Importantes
- A categoria `link_direto` tem amostra muito pequena (n≈1) — excluída dos testes estatísticos
- A distribuição de views é extremamente assimétrica → justifica Mann-Whitney (não-paramétrico)
- Apenas 1 snapshot do Spotify (12/03/2026) — limita análise temporal
