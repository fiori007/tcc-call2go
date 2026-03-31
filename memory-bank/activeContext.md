# Active Context — TCC Call2Go

## Foco Atual (Fase 6 — Correções de Precisão + Revalidação, 31/03/2026)
Revisão humana do ground truth pré-preenchido revelou erros em TODOS os 6 vídeos flagados. Correções extensas aplicadas no detector (6 fixes), MJ Records removido (dados contaminados — label brasileira mapeada para canal do Michael Jackson), testes estatísticos corrigidos. Pipeline re-executado com sucesso. Novo ground truth pré-preenchido gerado (49 alta confiança, 1 para revisão). Aguardando validação humana final.

## Estado do Projeto (31/03/2026)

### Coleta de Dados ✅
- **Artistas:** 49 artistas brasileiros (MJ Records REMOVIDO — canal incorreto)
- **Vídeos YouTube:** 980 vídeos (20 mais visualizados por artista), 0 erros
- **Spotify:** Métricas coletadas para 50 artistas (popularity + followers)
- **Canal scraping:** 52 canais processados, 29 com link Spotify no About, 2 OAC detectados

### Detector Call2Go ✅ (6 correções aplicadas em 31/03)
- **3 camadas de link:** domínio direto Spotify + redirect com label Spotify + URL com spotify/sptfy no path
- **Padrões implícitos:** range limitado `.{0,50}` (era `.*` — causava falsos positivos)
- **Fonte `ambos`:** nova opção quando vídeo E canal têm Call2Go
- **Seed channel fallback:** corrige mismatch de channel_id (Anitta, Panda, Turma do Pagode, Léo Santana)
- **Resultados:** 575 link_direto (58.7%), 0 texto_implicito (0%), 405 nenhum (41.3%)
- **Fontes:** 494 canal (50.4%), 66 ambos (6.7%), 15 video (1.5%), 405 nenhum (41.3%)
- **Auto-gerados:** 40 vídeos (4.1%), 940 orgânicos

### Análises Estatísticas ✅ (corrigidas — agora comparam Call2Go vs nenhum)
- **EDA:** link_direto média 46.1M views vs nenhum 19.1M (N=1240 registros cruzados)
- **Mann-Whitney U:** U=118004, p=0.35983 — **NÃO REJEITA H0** (Call2Go → mais views: não significativo)
- **Cross-platform:** U=169415.5, p=0.99819 — **NÃO REJEITA H0** (Call2Go não impacta Spotify pop)
  - Média Pop Sem Call2Go: 74.77 vs Com Call2Go: 73.58
- **Validação bidirecional:**
  - Direção A (YouTube→Spotify): Call2Go Rate ↔ Spotify Pop: ρ=-0.086, p=0.556 (**NÃO significativo**)
  - Direção B (Spotify→YouTube): Spotify Pop ↔ YT Avg Views: ρ=0.392, p=0.0054 (**SIGNIFICATIVO***)
  - **Classificação: UNIDIRECIONAL Spotify → YouTube** (α=0.1)

### Data Warehouse ✅
- SQLite: `data/processed/call2go.db` com 3 tabelas (dim_artist, fact_yt_videos, fact_spotify_metrics)

### Validação ✅
- Amostra de 50 vídeos (seed=42, de 980 total)
- Ground truth: 29 link_direto, 0 texto_implicito, 21 nenhum (50/50 alta confiança)
- Eric Land (tmAsMpFERrE): corrigido — menção narrativa no canal NÃO conta como has_spotify_text
- **Cross-validation (humano vs. máquina):**
  - Nível 1 (só vídeo): Acurácia 60% (P=100%/51%, R=31%/100%)
  - **Nível 2 (vídeo+canal): Acurácia 100% — Precisão 100%, Recall 100%, F1 100%**
  - **Nível 3 (só canal): Acurácia 100%**
- Matrizes de confusão e gráficos de métricas gerados em data/plots/

## ⚠️ Questão Metodológica Aberta
A **Direção B ("Spotify → YouTube")** na validação bidirecional NÃO usa dados de links reais do Spotify apontando para o YouTube. É puramente correlação estatística entre Spotify popularity e YouTube avg_views. Pode ser variável confundidora (fama geral). **Pendente alinhamento com orientador.**

## Próximas Ações (Prioridade)
1. ✅ Ground truth revisado e salvo (Eric Land corrigido)
2. ✅ Cross-validator executado — **100% acurácia (Nível 2 combinado)**
3. ✅ Agreement report gerado — matrizes de confusão e gráficos
4. [ ] Commit e push de todos os dados e artefatos
5. 🔴 **ALUNO:** Alinhar com orientador sobre interpretação da Direção B
6. [ ] Documentar para texto do TCC
