# Active Context — TCC Call2Go

## Foco Atual (Fase 7 — Auditoria Profissional + Reconstrução da Validação, 07/04/2026)
Auditoria completa revelou que os 100% de acurácia Nível 2/3 eram INVÁLIDOS — validação circular confirmada (ground_truth.csv idêntico ao prefilled). Reconstruída a validação com: amostra adversarial estratificada (91 vídeos), anotador cego, Cohen's Kappa + bootstrap IC 95%. Encoding fix em 14 arquivos. 77 testes unitários criados. **Aguardando anotação humana cega.**

## Estado do Projeto (07/04/2026)

### Coleta de Dados ✅
- **Artistas:** 49 artistas brasileiros (MJ Records REMOVIDO — canal incorreto)
- **Vídeos YouTube:** 980 vídeos (20 mais visualizados por artista), 0 erros
- **Spotify:** Métricas coletadas para 50 artistas (popularity + followers)
- **Canal scraping:** 52 canais processados, 29 com link Spotify no About, 2 OAC detectados

### Detector Call2Go ✅
- 575 link_direto (58.7%), 0 texto_implicito (0%), 405 nenhum (41.3%)
- Fontes: 494 canal, 66 ambos, 15 video, 405 nenhum
- 77 testes unitários adversariais — 100% passam
- Determinístico e reprodutível (SHA256 verificado)

### Análises Estatísticas ✅
- **Mann-Whitney:** U=118004, p=0.36 — NÃO REJEITA H0
- **Cross-platform:** U=104647.5, p=0.997 — NÃO REJEITA H0
- **Bidirecional:** UNIDIRECIONAL Spotify -> YouTube (rho=0.392, p=0.005)

### Validação — RECONSTRUÍDA (Fase 7)
- **PROBLEMA DESCOBERTO:** ground_truth.csv == ground_truth_prefilled.csv (SHA256 idêntico)
  - cross_validator comparava detector consigo mesmo → 100% era tautologia
  - Kappa Nível 1 (video-only) = 0.27 (razoável) — este era o resultado honesto
  - Kappa Nível 2-3 = 1.0 — circular, inválido
- **SOLUÇÃO:**
  - adversarial_sampler.py: 91 vídeos estratificados (9 estratos, cobrindo todos os edge cases)
  - blind_annotator.py: CSV cego sem sugestões do detector
  - cross_validator.py: +Cohen's Kappa, +bootstrap IC 95%, suporte formato novo
  - agreement_report.py: +Kappa no resumo

### Testes ✅ (NOVO)
- tests/test_call2go_detector.py: 77 testes em 11 grupos — todos passam
- Cobertura: links diretos, redirects, texto implícito, narrativas, edge cases, auto-gerado, canal, scraped

### Pipeline ✅
- Roda sem erros em Windows cp1252 (encoding fix aplicado)
- 11 etapas, 5.9s (skip-collect)
- requirements.txt totalmente pinado + scikit-learn + pytest

## Próximas Ações (Prioridade)
1. 🔴 **ALUNO:** Anotar `data/validation/blind_annotation.csv` (91 vídeos, SEM olhar o prefilled)
2. 🔴 **ALUNO:** Salvar como `data/validation/ground_truth.csv`
3. [ ] Rodar `python -m src.validation.cross_validator` com ground truth real
4. [ ] Rodar `python -m src.validation.agreement_report`
5. 🔴 **ALUNO:** Alinhar com orientador sobre Direção B (correlação vs. links reais)
6. [ ] Escrever capítulo de Metodologia documentando a correção da validação circular
