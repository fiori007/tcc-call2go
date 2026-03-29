# Active Context — TCC Call2Go

## Foco Atual (Fase 4 — Qualidade dos Dados, 29/03/2026)
Qualidade dos dados significativamente melhorada. Web scraper extrai links estruturados do YouTube, filtro de auto-gerados remove 45% de vídeos poluentes, detecção narrativa elimina falsos positivos.

## Estado do Projeto (29/03/2026)
- Coleta de dados do Spotify e YouTube: **concluída** (20 artistas, 1000 vídeos)
- Detector Call2Go (regex): **melhorado** (3 níveis: vídeo + canal texto + canal scraped)
- Filtro auto-gerados: **implementado** (450/1000 vídeos = 45% são auto-gerados)
- Web scraper canais: **implementado** (12/20 artistas com Spotify no About, 9/20 OAC, 9/9 oficiais descobertos)
- Filtro narrativo: **implementado** ("charts do Spotify" ≠ Call2Go)
- Data Warehouse SQLite: **construído**
- Análises estatísticas: **concluídas** (mas resultados não validados)
- Ground truth pré-preenchido: **50/50 alta confiança** ✅
- Distribuição: 31 link_direto, 0 texto_implicito, 19 nenhum

## Próximas Ações (Prioridade)
1. 🔴 **ALUNO:** Revisar `data/validation/ground_truth_prefilled.csv` (50 vídeos, todos alta confiança)
2. 🔴 **ALUNO:** Salvar como `data/validation/ground_truth.csv`
3. [ ] Rodar `cross_validator.py` — métricas de confiabilidade
4. [ ] Rodar `agreement_report.py` — gráficos para o TCC
5. [ ] Rodar `cross_platform_validator.py` — análise bidirecional
6. [ ] Re-rodar análises estatísticas sobre dados validados
7. [ ] Documentar para texto do TCC
