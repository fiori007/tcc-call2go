# Active Context — TCC Call2Go

## Foco Atual (Pós-Alinhamento com Orientador — 28/03/2026)
**MUDANÇA DE FOCO:** O projeto deixou de ser sobre "impacto do Call2Go em artistas" e passou a ser sobre **confiabilidade metodológica** — validar se o detector automatizado é confiável antes de confiar nos resultados.

A "volta" (validação cruzada humano vs. máquina) é agora o artefato central do TCC.

## Problemas Identificados pelo Orientador
1. **Base de artistas sem critério científico** — veio de IA (Gemini) sem fonte oficial
2. **IA como fonte de verdade** — pipeline sem verificação independente
3. **Sem validação manual** — nenhuma etapa de "volta" existia
4. **Foco errado** — estava focado em música, deveria focar em metodologia

## Estado do Projeto (28/03/2026)
- Coleta de dados do Spotify e YouTube: **concluída** (mas base de artistas precisa ser refeita)
- Detector Call2Go (regex): **concluído** (mas precisa ser VALIDADO)
- Data Warehouse SQLite: **construído**
- Análises estatísticas: **concluídas** (mas resultados não validados)
- **NOVO:** `artist_source_builder.py` — fonte oficial via playlists Spotify ✅
- **NOVO:** `sample_generator.py` — gera amostra para anotação manual ✅
- **NOVO:** `cross_validator.py` — a "volta" (humano vs. máquina) ✅
- **NOVO:** `agreement_report.py` — relatório visual de concordância ✅

## Próximas Ações (Prioridade)
1. [ ] **Rodar `artist_source_builder.py`** para gerar nova base de artistas com fonte oficial
2. [ ] **Re-coletar dados** do YouTube com a nova base
3. [ ] **Rodar `sample_generator.py`** para gerar amostra de validação
4. [ ] **Anotar manualmente** o ground truth (o aluno, não a IA)
5. [ ] **Rodar `cross_validator.py`** para medir confiabilidade
6. [ ] **Rodar `agreement_report.py`** para gerar gráficos de concordância
7. [ ] Só então rodar as análises estatísticas sobre dados validados
8. [ ] Documentar todo o processo para o texto do TCC
