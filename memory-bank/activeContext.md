# Active Context — TCC Call2Go

## Foco Atual
Pipeline completo de coleta → processamento → análise implementado e funcional.

## Estado do Projeto (28/03/2026)
- Coleta de dados do Spotify e YouTube: **concluída**
- Detector Call2Go (NLP via regex): **concluído e testado**
- Data Warehouse SQLite: **construído e populado**
- Análise exploratória (EDA): **concluída** — boxplots gerados
- Teste de hipótese (Mann-Whitney U): **concluído**
- Análise cross-platform (YouTube → Spotify): **concluída** — scatter plot gerado

## Decisões Recentes
- Escolha do Mann-Whitney U em vez de t-test: distribuição de views é altamente assimétrica (não-normal), exigindo teste não-paramétrico
- Escala logarítmica nos gráficos: necessária pela disparidade extrema de views (40K vs 16M)
- Exclusão de `link_direto` do teste estatístico: amostra muito pequena (n≈1), insuficiente para inferência

## Próximas Ações Possíveis
- [ ] Expandir amostra de artistas
- [ ] Adicionar notebooks Jupyter para apresentação interativa
- [ ] Adicionar análise temporal (evolução das métricas ao longo do tempo)
- [ ] Documentar limitações e vieses no TCC
- [ ] Considerar teste de correlação (Spearman) para views × popularity

## Dúvidas em Aberto
- A pasta `notebooks/` está vazia — será usada?
- Há plano para coleta longitudinal (múltiplas datas do Spotify)?
- O `call2go_detector` cobre todos os padrões relevantes ou precisa de refinamento?
