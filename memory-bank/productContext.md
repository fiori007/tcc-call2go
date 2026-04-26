# Product Context — TCC Call2Go

## Problema de Pesquisa
A indústria musical brasileira depende cada vez mais de estratégias cross-platform para maximizar o alcance de artistas. Uma prática comum é incluir chamadas (Call2Go) nas descrições de vídeos do YouTube direcionando a audiência para plataformas de streaming como o Spotify. No entanto, **não há evidência empírica consolidada** sobre a eficácia real dessa estratégia.

## Por que isso importa?
- **Para artistas/labels:** Saber se vale a pena investir em Call2Go ou se é esforço desperdiçado
- **Para a academia:** Contribuir com dados empíricos sobre marketing musical digital no Brasil
- **Para o mercado:** Entender o comportamento cross-platform do consumidor de música

## Contexto do Mercado
- O Brasil é um dos maiores mercados de música digital do mundo
- YouTube e Spotify são as duas plataformas dominantes para consumo de música
- Artistas sertanejos e pop brasileiros investem pesado em presença digital
- A relação entre views no YouTube e streams no Spotify não é linear nem óbvia

## Público-Alvo do Estudo
- Banca acadêmica do TCC
- Profissionais de marketing musical
- Pesquisadores em comunicação digital e comportamento do consumidor

## Evolução da Validação (Cronologia)
| Fase | Data | Ação | Resultado |
|------|------|------|-----------|
| 3 | Mar/2026 | Validação circular (ground_truth_helper) | DESCARTADA |
| 5-6 | 31/03 | 6 fixes no detector (redirects, labeled, greedy) | Detector melhorado |
| 8 | 10/04 | 91 vídeos adversariais, anotação cega | **BASELINE DEFINITIVO** |
| Cleanup | 18/04 | Remocao ground_truth.csv (fase 3 circular) | Higiene metodológica |
| 11 | 26/04 | Ranking Fusion v3.0, 288 artistas | Analise concluída |
| 12 | 26/04 | Census annotation descontinuado | **Decisao definitiva** |

## Decisão: Descontinuação da Anotação Censitária (26/04/2026)
**Motivo:** Após 6 iteracoes de auditoria e fix, o detector alcançou Kappa=0.80 em canal
(substancial) e 82.4% acurácia em vídeo. Anotar 1.641 vídeos adicionalmente
não muda as conclusões e não é rastreavel (viesa confirmatório potencial).
O TCC tem como foco a metodologia, não a escala da amostra. 91 vídeos adversariais
representam um rigor analítico maior do que 1.641 vídeos com anotação não-cega.

## Definições-Chave
- **Call2Go:** Qualquer elemento na descrição de um vídeo do YouTube que direcione o espectador para o Spotify (link direto ou texto implícito)
- **Cross-Platform:** Transferência de engajamento/audiência entre YouTube e Spotify
- **Popularity Score (Spotify):** Índice algorítmico de 0-100 baseado em streams recentes, não é público como o cálculo funciona exatamente
