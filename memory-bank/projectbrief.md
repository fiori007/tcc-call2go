# Project Brief — TCC Call2Go

## Título do Trabalho
Análise do Impacto de Estratégias "Call2Go" em Vídeos do YouTube sobre Métricas Cross-Platform no Spotify

## Objetivo Principal
Investigar se a presença de chamadas de direcionamento para o Spotify (Call2Go) nas descrições de vídeos do YouTube de artistas brasileiros influencia:
1. O volume de visualizações no YouTube
2. A popularidade cross-platform do artista no Spotify

## Hipóteses de Pesquisa
- **H0 (Nula):** Não há diferença significativa de views entre vídeos com e sem Call2Go.
- **H1 (Alternativa — YouTube):** Vídeos com Call2Go implícito geram maior volume de visualizações.
- **H2 (Alternativa — Cross-Platform):** O uso de Call2Go no YouTube impacta positivamente a popularidade no Spotify.

## Escopo
- **Amostra:** 6 artistas brasileiros de grande porte (Anitta, Marília Mendonça, Henrique e Juliano, Luan Santana, Zé Neto e Cristiano, Gusttavo Lima)
- **Volume:** ~50 vídeos mais recentes por artista (~300 vídeos no total)
- **Métricas YouTube:** views, likes, comentários
- **Métricas Spotify:** followers, popularity (índice 0-100)
- **Método de detecção:** Regex/NLP sobre descrições dos vídeos
- **Teste estatístico:** Mann-Whitney U (não paramétrico), α = 0.05

## Classificação Call2Go
| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| `link_direto` | Links Spotify na descrição | `https://open.spotify.com/...`, `spoti.fi/...` |
| `texto_implicito` | Menções textuais ao Spotify | "ouça no Spotify", "disponível no Spotify" |
| `nenhum` | Sem qualquer referência ao Spotify | — |

## Entregáveis Acadêmicos
- Gráficos com DPI 300 (padrão banca)
- Testes estatísticos com nível de confiança de 95%
- Data Warehouse relacional (SQLite) documentado
- Pipeline ETL reprodutível
