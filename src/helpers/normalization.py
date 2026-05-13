"""Normalizacao canonica de nomes de artistas e faixas.

Funcao unica usada por todos os modulos do projeto. Substitui as 6
implementacoes ad-hoc anteriores que divergiam em forma Unicode (NFC vs
NFKD vs NFD) e podiam causar falhas silenciosas de matching.

Forma canonica: NFKD + remocao de combining marks + lowercase +
substituicao de pontuacao por espaco + colapso de espacos.
"""

import re
import unicodedata


_PUNCT_RE = re.compile(r"[^\w\s]")
_SPACE_RE = re.compile(r"\s+")


def normalize_name(name) -> str:
    """Normaliza nome de artista/faixa para matching cross-source.

    Args:
        name: string a normalizar; tipos nao-string retornam string vazia.

    Returns:
        String normalizada em ASCII lowercase, sem pontuacao nem acentos,
        com espacos colapsados.
    """
    if not isinstance(name, str):
        return ""
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    norm = norm.lower()
    norm = _PUNCT_RE.sub(" ", norm)
    norm = _SPACE_RE.sub(" ", norm).strip()
    return norm
