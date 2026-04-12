# Active Context — TCC Call2Go

## Estado Atual (12/04/2026 — Fase 9c Completa)
Projeto limpo, consistente e preparado para futura re-execução. Lógica combinado corrigida para AND (vídeo E canal), detecção de canal normalizada via seed (artistas.csv). XLSX censo com 920 vídeos pronto para anotação humana.

**Próximo passo:** 🔴 Alinhar com orientador, depois anotar TODOS os 920 vídeos no XLSX censo (SIM/NÃO), salvar como ground_truth.csv, e rodar cross_validator.

## Dados Atuais
- **Artistas:** 50 no seed, 46 com vídeos coletados
- **Vídeos:** 920 (20 mais visualizados por artista)
- **Spotify:** Métricas coletadas em 11/04/2026
- **Canais scrapeados:** 51 canais com links da aba Sobre
- **Testes:** 77 unitários — todos passam

## Lógica de Detecção
- **Vídeo:** regex na descrição do vídeo (detect_call2go)
- **Canal:** links estruturados scrapeados da aba Sobre (detect_call2go_channel_scraped)
  - Prioridade: canal oficial do seed (artistas.csv), fallback pelo channel_id do JSONL
- **Combinado:** AND — vídeo E canal devem ter Call2Go (has_call2go AND final_channel_has)
- **Fonte:** `ambos` quando combinado=True, senão `nenhum`

## Artefatos Prontos
- `data/validation/blind_annotation_census.xlsx` — 920 vídeos, dropdowns SIM/NÃO
- `data/validation/detector_answers_census.xlsx` — respostas do detector (referência)
- `data/processed/youtube_call2go_flagged.csv` — flags de detecção
- `data/processed/call2go.db` — Data Warehouse SQLite

## Próximas Ações (Prioridade)
1. [P0] 🔴 **Alinhar com orientador** sobre resultados e interpretação
2. [P1] 🔴 **Anotar 920 vídeos** em blind_annotation_census.xlsx → salvar como ground_truth.csv
3. [P2] Rodar `python -m src.validation.cross_validator` para validação censitária
4. [P3] Escrever capítulo de Metodologia (validação circular → correção → AND)
5. [P4] Escrever capítulo de Resultados com Kappa 3 níveis + IC 95%

## Referência — Fase 8 (91 vídeos, Amostra Adversarial)
Resultados com lógica OR (OBSOLETOS — detector usava OR, humano usava AND):
- Vídeo: Kappa 0.4493 (moderado)
- Canal: Kappa 0.8040 (substancial)
- Combinado: Kappa 0.0947 (fraco — artefato AND/OR)
