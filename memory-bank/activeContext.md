# Active Context — TCC Call2Go

## Foco Atual (Fase 8 — A Volta: Cross-Validation Real, 10/04/2026)
Anotação humana cega de 91 vídeos adversariais concluída. Cross-validation executada com resultados REAIS:
- **Canal: Kappa 0.80 (substancial)** — detector confiável
- **Vídeo: Kappa 0.45 (moderado)** — detector conservador (recall 100%, precisão 36%)
- **Combinado: Kappa 0.09 (fraco)** — artefato metodológico AND vs OR, não falha do detector

**Próximo passo:** Escrita do TCC (Metodologia + Resultados) e alinhamento com orientador.

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

### Validação — CONCLUÍDA (Fases 7 + 8)
- **PROBLEMA (Fase 7):** ground_truth.csv == ground_truth_prefilled.csv (validação circular)
- **CORREÇÃO (Fase 7):** amostra adversarial (91), anotação cega, Kappa + bootstrap CI
- **RESULTADO REAL (Fase 8 — 10/04/2026):**
  - Nível Vídeo: Kappa 0.4493 [0.24, 0.64] — moderado (16 FPs, detector broad)
  - Nível Canal: Kappa 0.8040 [0.68, 0.91] — substancial (9 FNs, links não scrapeados)
  - Nível Combinado: Kappa 0.0947 [0.03, 0.17] — fraco (AND vs OR: artefato, não falha)

### Testes ✅ (NOVO)
- tests/test_call2go_detector.py: 77 testes em 11 grupos — todos passam
- Cobertura: links diretos, redirects, texto implícito, narrativas, edge cases, auto-gerado, canal, scraped

### Pipeline ✅
- Roda sem erros em Windows cp1252 (encoding fix aplicado)
- 11 etapas, 5.9s (skip-collect)
- requirements.txt totalmente pinado + scikit-learn + pytest

## Próximas Ações (Prioridade)
1. 🔴 **ALUNO:** Alinhar com orientador sobre Direção B (correlação vs. links reais Spotify→YouTube)
2. [ ] Escrever capítulo de Metodologia documentando validação circular + correção + resultados reais
3. [ ] Escrever capítulo de Resultados com Kappa 3 níveis + IC 95% + matrizes de confusão
4. [ ] Analisar os 16 FPs do nível Vídeo — entender por que o detector marca mas o humano não
5. [ ] Analisar os 9 FNs do nível Canal — links Spotify não scrapeados (lnk.to, etc.)
