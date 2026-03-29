# Active Context — TCC Call2Go

## Foco Atual (Fase 3 — Automação da Validação, 29/03/2026)
Pipeline de validação semi-automático implementado. O aluno precisa apenas revisar 5 vídeos de média confiança e salvar o ground truth.

## Estado do Projeto (29/03/2026)
- Coleta de dados do Spotify e YouTube: **concluída** (20 artistas, 1000 vídeos)
- Detector Call2Go (regex): **corrigido** (adicionado `sptfy.com`)
- Data Warehouse SQLite: **construído**
- Análises estatísticas: **concluídas** (mas resultados não validados)
- **NOVO:** `ground_truth_helper.py` — pré-preenche ground truth automaticamente ✅
- `sample_generator.py` — atualizado com `channel_description_preview` ✅
- `cross_validator.py` — atualizado com validação em 3 níveis (vídeo/combinado/canal) ✅
- `agreement_report.py` — atualizado com 2 matrizes + imagens ≤1800px ✅
- Ground truth pré-preenchido: 45/50 alta confiança, 5 para revisão ✅

## Próximas Ações (Prioridade)
1. 🔴 **ALUNO:** Revisar `data/validation/ground_truth_prefilled.csv` (5 vídeos)
2. 🔴 **ALUNO:** Salvar como `data/validation/ground_truth.csv`
3. [ ] Rodar `cross_validator.py` — métricas de confiabilidade
4. [ ] Rodar `agreement_report.py` — gráficos para o TCC
5. [ ] Rodar `cross_platform_validator.py` — análise bidirecional
6. [ ] Re-rodar análises estatísticas sobre dados validados
7. [ ] Documentar para texto do TCC
7. [ ] Só então rodar as análises estatísticas sobre dados validados
8. [ ] Documentar todo o processo para o texto do TCC
