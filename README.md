# TCC Call2Go

Pipeline de analise empirica da efetividade das estrategias **Call2Go**
(chamadas cross-platform YouTube to Spotify) na industria musical brasileira.
O detector regex e o **instrumento de mensuracao** (validado, Kappa canal 0,80);
a efetividade do cross-platform e o **objeto de estudo**.

> Contexto detalhado em [`memory-bank/`](memory-bank/) (gitignored, local-only).

## Pre-requisitos

- Python **3.12.9** (ver [`.python-version`](.python-version))
- Windows / PowerShell (encoding cp1252-safe; o pipeline foi desenhado para rodar nesse ambiente)
- Conta nas APIs Spotify, YouTube Data v3 e Last.fm (chaves no `.env`)

## Setup

```powershell
# 1. Clone e crie o ambiente virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Instale dependencias
pip install -r requirements.txt

# 3. Crie o .env a partir do template
copy .env.example .env
# edite .env com suas chaves: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET,
# YOUTUBE_API_KEY, LASTFM_API_KEY
```

## Comandos do pipeline

```powershell
# Apenas analises (uso mais comum -- nao consome quota das APIs)
python run_pipeline.py --skip-collect

# Pipeline completo (coleta + analise)
python run_pipeline.py

# A partir de uma etapa especifica
python run_pipeline.py --from-step 6

# Forcar re-scraping de canais (ignora cache)
python run_pipeline.py --force-channel-scrape
```

### Sincronizar figuras para os documentos LaTeX

O pipeline grava figuras em `data/plots/` e `data/validation/`. Os documentos
(artigo e colinha) leem de `artigo_latex/figs/`. Apos (re)gerar os graficos,
sincronize com o mapa explicito em [`scripts/sync_figures.py`](scripts/sync_figures.py):

```powershell
python run_pipeline.py --skip-collect --strict   # regenera os graficos
python scripts/sync_figures.py                    # data/plots + data/validation -> artigo_latex/figs
# entao recompilar o LaTeX (artigo e colinha)
```

## Estrutura

```
tcc_call2go/
  run_pipeline.py            # Orquestrador (20 etapas)
  scripts/sync_figures.py    # Sincroniza figuras do pipeline -> artigo_latex/figs
  requirements.txt           # Dependencias pinadas
  src/
    config.py                # Constantes centrais (paths, alphas, seeds)
    collectors/              # Coleta APIs + scraping (YouTube, Spotify, Last.fm)
    processors/              # Detector Call2Go + processamento de charts
    db/                      # Data Warehouse SQLite (batch/rebuild)
    analytics/               # EDA, testes de hipotese, ranking fusion, temporal
    validation/              # Cross-validation, auditoria de links, regex audit
  tests/                     # Testes unitarios do detector (95 testes)
  data/
    seed/                    # artistas.csv (67 artistas)
    raw/                     # JSONL/CSV brutos das APIs
    processed/               # Flagged CSV, SQLite DB, ranking fusion
    plots/                   # Graficos PNG (DPI 300)
    validation/              # Relatorios de validacao
```

## Testes

```powershell
pytest tests/ -v
```

## Resultados e artigo

Os resultados estatisticos finais e o artigo LaTeX (formato SBC) ficam em
`artigo_latex/` (gitignored, local-only). Nao incluidos neste README por design --
este arquivo serve a quem precisa **rodar o codigo**, nao a quem precisa
**ler o trabalho**.

## Licenca / Autoria

Lucas Fiori Magalhaes Machado -- PUC Minas -- TCC 2026
