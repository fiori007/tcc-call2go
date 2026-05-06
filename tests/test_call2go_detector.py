"""
Testes adversariais para o detector Call2Go (call2go_detector.py).
Cobertura: links diretos, redirects, texto implícito, narrativas,
edge cases, Unicode, strings vazias, e inputs malformados.
"""
from src.processors.call2go_detector import (
    detect_call2go,
    detect_call2go_channel,
    detect_call2go_channel_scraped,
    is_auto_generated,
    _is_narrative_mention,
)
import pytest
import sys
import os

# Garante que o diretório raiz do projeto esteja no path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))


# =====================================================================
# GRUPO 1: Links diretos — Domínios oficiais do Spotify
# =====================================================================

class TestDirectLinks:
    """Testa detecção de links diretos para domínios oficiais do Spotify."""

    def test_open_spotify_com(self):
        text = "Ouça agora: https://open.spotify.com/track/1234567890"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_spoti_fi(self):
        text = "Link: https://spoti.fi/3abc123"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_sptfy_com(self):
        text = "Escute em http://sptfy.com/abc123"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_spotify_link_com_query_params(self):
        text = "https://open.spotify.com/track/abc?si=def123&utm_source=copy-link"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_spotify_link_http_sem_s(self):
        text = "http://open.spotify.com/artist/99999"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_spotify_link_maiusculo_nao_detecta(self):
        """Links em maiúsculo: text.lower() aplicado, deve detectar."""
        text = "HTTPS://OPEN.SPOTIFY.COM/TRACK/ABC123"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_link_spotify_no_meio_de_texto_longo(self):
        text = ("A" * 500 + " https://open.spotify.com/track/123 " + "B" * 500)
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_multiplos_links_retorna_primeiro(self):
        text = "https://open.spotify.com/a https://spoti.fi/b"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'


# =====================================================================
# GRUPO 2: Redirect links com label Spotify
# =====================================================================

class TestRedirectLinks:
    """Testa detecção de links redirect rotulados como Spotify."""

    def test_spotify_colon_lnk_to(self):
        text = "Spotify: https://lnk.to/meualbum"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_spotify_pipe_bit_ly(self):
        text = "Spotify | https://bit.ly/minhamusica"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_spotify_dash_smarturl(self):
        text = "Spotify - https://smarturl.it/meutrack"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_spotify_endash_url(self):
        text = "Spotify \u2013 https://example.com/track"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_url_com_spotify_no_path(self):
        """bit.ly/LivinhoNoSpotify → contém 'spotify' no path."""
        text = "Ouça: https://bit.ly/LivinhoNoSpotify"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_url_com_sptfy_no_path(self):
        text = "https://smarturl.it/mj_otw_sptfy"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'


# =====================================================================
# GRUPO 3: Links redirect SEM label Spotify (falsos positivos potenciais)
# =====================================================================

class TestRedirectSemLabel:
    """Links genéricos SEM 'spotify' no path/label → devem ser 'nenhum'."""

    def test_bit_ly_generico_sem_spotify(self):
        text = "Link: https://bit.ly/meuvideo"
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'

    def test_lnk_to_sem_contexto(self):
        text = "https://lnk.to/meualbum"
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'

    def test_smarturl_sem_spotify(self):
        text = "Link: https://smarturl.it/meuprojeto"
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'


# =====================================================================
# GRUPO 4: Texto implícito (CTAs reais)
# =====================================================================

class TestTextoImplicito:
    """Testa detecção de chamadas textuais para o Spotify."""

    def test_ouca_no_spotify(self):
        text = "Ouça no Spotify agora!"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'texto_implicito'

    def test_ouca_sem_cedilha(self):
        text = "Ouca no Spotify"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'texto_implicito'

    def test_disponivel_no_spotify(self):
        text = "Disponível no Spotify e em todas as plataformas"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'texto_implicito'

    def test_disponivel_sem_acento(self):
        text = "Disponivel no Spotify"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'texto_implicito'

    def test_stream_spotify(self):
        text = "Stream this song on Spotify"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'texto_implicito'

    def test_ouvir_no_spotify(self):
        text = "Você pode ouvir essa música no Spotify"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'texto_implicito'

    def test_ouca_artista_no_spotify(self):
        """Padrão real: 'Ouça MC Livinho no Spotify'."""
        text = "Ouça MC Livinho no Spotify"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'texto_implicito'

    def test_cta_com_excesso_de_palavras_no_meio(self):
        """Range limitado .{0,50} → muitas palavras não devem casar."""
        text = "Ouça " + "uma coisa incrível " * 5 + "no Spotify"
        # len("uma coisa incrível " * 5) = 95 chars > 50
        has, typ = detect_call2go(text)
        # Deve falhar no pattern limitado, mas pegar no fallback \bspotify\b
        # Resultado depende se fallback ativa (não é narrativa)
        assert has == 1  # fallback pega

    def test_stream_spotify_distante_demais(self):
        """Range .{0,50}: texto entre 'stream' e 'spotify' > 50 chars."""
        text = "Stream " + "x" * 60 + " spotify"
        has, typ = detect_call2go(text)
        # Padrão limitado não pega, mas fallback \bspotify\b deve pegar
        assert has == 1


# =====================================================================
# GRUPO 5: Menções narrativas (NÃO são Call2Go)
# =====================================================================

class TestNarrativas:
    """Menções ao Spotify como contexto/branding, não como CTA."""

    def test_charts_do_spotify(self):
        assert _is_narrative_mention("charts do spotify") is True

    def test_ranking_no_spotify(self):
        assert _is_narrative_mention("ranking no spotify") is True

    def test_top_10_do_spotify(self):
        assert _is_narrative_mention("top 10 do spotify") is True

    def test_milhoes_de_plays_no_spotify(self):
        assert _is_narrative_mention("5 milhões de plays no spotify") is True

    def test_dias_nos_charts(self):
        assert _is_narrative_mention("200 dias nos charts") is True

    def test_hashtag_numero_no_spotify(self):
        assert _is_narrative_mention("#1 no spotify") is True

    def test_narrativa_nao_conta_como_call2go(self):
        """Texto com menção narrativa ao Spotify não deve ser Call2Go."""
        text = "200 dias nos charts do Spotify! Artista mais ouvido do Brasil."
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'

    def test_top_50_no_spotify(self):
        text = "Entrou no Top 50 do Spotify essa semana!"
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'

    def test_milhoes_streams_spotify(self):
        text = "Atingiu 10 milhões de streams no Spotify"
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'

    def test_mencao_pura_sem_narrativa_E_call2go(self):
        """'Spotify' sozinho sem narrativa → fallback ativa → texto_implicito."""
        text = "Siga no Spotify e Instagram"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'texto_implicito'


# =====================================================================
# GRUPO 6: Inputs inválidos / edge cases
# =====================================================================

class TestEdgeCases:
    """Testa comportamento com inputs inválidos, vazios, e edge cases."""

    def test_none(self):
        has, typ = detect_call2go(None)
        assert has == 0 and typ == 'nenhum'

    def test_string_vazia(self):
        has, typ = detect_call2go("")
        assert has == 0 and typ == 'nenhum'

    def test_numero(self):
        has, typ = detect_call2go(12345)
        assert has == 0 and typ == 'nenhum'

    def test_booleano(self):
        has, typ = detect_call2go(True)
        assert has == 0 and typ == 'nenhum'

    def test_lista(self):
        has, typ = detect_call2go(["https://open.spotify.com/track/123"])
        assert has == 0 and typ == 'nenhum'

    def test_texto_sem_spotify(self):
        text = "Veja o clipe oficial no YouTube. Inscreva-se no canal!"
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'

    def test_texto_so_espacos(self):
        has, typ = detect_call2go("   \n\t  ")
        assert has == 0 and typ == 'nenhum'

    def test_url_spotify_falsa(self):
        """Domínio que parece Spotify mas não é."""
        text = "https://open.spotify.fake.com/track/123"
        has, typ = detect_call2go(text)
        # Contém 'spotify' no path → será capturado pelo pattern 1c
        assert has == 1  # O detector PEGA isso (potencial falso positivo)

    def test_url_notspotify_com(self):
        """Subdomínio 'notspotify.com' → contém 'spotify' na URL."""
        text = "https://notspotify.com/track/123"
        has, typ = detect_call2go(text)
        assert has == 1  # Detector pega — é um falso positivo conhecido

    def test_spotify_em_email(self):
        """Email com spotify no domínio."""
        text = "Contato: artista@spotify.com"
        has, typ = detect_call2go(text)
        # \bspotify\b fallback pega → texto_implicito
        assert has == 1

    def test_unicode_homoglyph(self):
        """'Ꮪpotify' com S em Cherokee → não deve casar."""
        text = "Ouça no \u13d5potify"  # Ꮪ = Cherokee S
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'


# =====================================================================
# GRUPO 7: Função is_auto_generated()
# =====================================================================

class TestAutoGenerated:
    """Testa detecção de vídeos auto-gerados (Content ID)."""

    def test_provided_to_youtube(self):
        text = "Provided to YouTube by DistroKid\n\nSong Title..."
        assert is_auto_generated(text) is True

    def test_auto_generated_by_youtube(self):
        text = "Auto-generated by YouTube.\n\nMusic video..."
        assert is_auto_generated(text) is True

    def test_provided_case_insensitive(self):
        text = "PROVIDED TO YOUTUBE BY Universal Music\n"
        assert is_auto_generated(text) is True

    def test_descricao_normal(self):
        text = "Veja o clipe oficial da faixa..."
        assert is_auto_generated(text) is False

    def test_provided_nao_primeira_linha(self):
        """'Provided to YouTube' NÃO na primeira linha → não é auto-gen."""
        text = "Clipe oficial\nProvided to YouTube by Sony"
        assert is_auto_generated(text) is False

    def test_vazio(self):
        assert is_auto_generated("") is False
        assert is_auto_generated(None) is False


# =====================================================================
# GRUPO 8: detect_call2go_channel()
# =====================================================================

class TestChannelDetection:
    """Testa detecção na bio do canal."""

    def test_channel_com_link_spotify(self):
        text = "Meu perfil: https://open.spotify.com/artist/12345"
        has, typ = detect_call2go_channel(text)
        assert has == 1 and typ == 'link_direto'

    def test_channel_sem_spotify(self):
        text = "Canal oficial de música brasileira. Inscreva-se!"
        has, typ = detect_call2go_channel(text)
        assert has == 0 and typ == 'nenhum'

    def test_channel_none(self):
        has, typ = detect_call2go_channel(None)
        assert has == 0 and typ == 'nenhum'

    def test_channel_vazio(self):
        has, typ = detect_call2go_channel("")
        assert has == 0 and typ == 'nenhum'

    def test_channel_spotify_narrativa(self):
        """Bio com menção narrativa → NÃO tem fallback genérico (por design)."""
        text = "Top 10 artistas do Spotify Brasil"
        has, typ = detect_call2go_channel(text)
        # channel NÃO tem fallback \bspotify\b → nenhum
        assert has == 0 and typ == 'nenhum'


# =====================================================================
# GRUPO 9: detect_call2go_channel_scraped()
# =====================================================================

class TestScrapedDetection:
    """Testa detecção via dados scrapeados (binary check)."""

    def test_canal_com_spotify_link(self):
        scraped = {
            "UC123": {
                "has_spotify": True,
                "spotify_links": ["https://open.spotify.com/artist/abc"]
            }
        }
        has, typ = detect_call2go_channel_scraped("UC123", scraped)
        assert has == 1 and typ == 'link_direto'

    def test_canal_sem_spotify(self):
        scraped = {
            "UC123": {"has_spotify": False, "spotify_links": []}
        }
        has, typ = detect_call2go_channel_scraped("UC123", scraped)
        assert has == 0 and typ == 'nenhum'

    def test_canal_nao_no_cache(self):
        scraped = {"UC999": {"has_spotify": True, "spotify_links": ["x"]}}
        has, typ = detect_call2go_channel_scraped("UC_INEXISTENTE", scraped)
        assert has == 0 and typ == 'nenhum'

    def test_scraped_data_none(self):
        has, typ = detect_call2go_channel_scraped("UC123", None)
        assert has == 0 and typ == 'nenhum'

    def test_scraped_data_vazio(self):
        has, typ = detect_call2go_channel_scraped("UC123", {})
        assert has == 0 and typ == 'nenhum'

    def test_oac_com_canal_oficial(self):
        """Canal OAC com canal oficial que tem Spotify."""
        scraped = {
            "UC_OAC": {
                "has_spotify": False,
                "spotify_links": [],
                "is_auto_generated_channel": True,
                "official_channel_id": "UC_OFICIAL",
                "official_spotify_links": []
            },
            "UC_OFICIAL": {
                "has_spotify": True,
                "spotify_links": ["https://open.spotify.com/artist/xyz"]
            }
        }
        has, typ = detect_call2go_channel_scraped("UC_OAC", scraped)
        assert has == 1 and typ == 'link_direto'

    def test_oac_com_official_spotify_links(self):
        """Canal OAC com links do oficial mesclados."""
        scraped = {
            "UC_OAC": {
                "has_spotify": False,
                "spotify_links": [],
                "official_spotify_links": ["https://open.spotify.com/artist/abc"]
            }
        }
        has, typ = detect_call2go_channel_scraped("UC_OAC", scraped)
        assert has == 1 and typ == 'link_direto'

    def test_has_spotify_true_mas_links_vazio(self):
        """has_spotify=True mas spotify_links=[] → não deve detectar."""
        scraped = {
            "UC123": {"has_spotify": True, "spotify_links": []}
        }
        has, typ = detect_call2go_channel_scraped("UC123", scraped)
        assert has == 0 and typ == 'nenhum'


# =====================================================================
# GRUPO 10: Testes de integração / cenários reais
# =====================================================================

class TestCenariosReais:
    """Testa com dados reais encontrados durante o desenvolvimento."""

    def test_anitta_lnk_to(self):
        """Caso Anitta: 'Spotify | https://Anitta.lnk.to/Spotify'."""
        text = "Spotify | https://Anitta.lnk.to/Spotify"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_mc_livinho_bit_ly(self):
        """Caso Mc Livinho: bit.ly/LivinhoNoSpotify."""
        text = "Spotify: https://bit.ly/LivinhoNoSpotify"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_nattan_bio_narrativa(self):
        """Caso NATTAN: bio longa com 'stream...spotify' > 50 chars."""
        text = ("NATTAN é um dos artistas mais ouvidos do Brasil " +
                "com milhões de streams em diversas plataformas incluindo o spotify")
        # 'stream' e 'spotify' estão a > 50 chars de distância
        # O pattern limitado não deve casar
        # Mas \bspotify\b fallback existe... verificar se narrativa
        has, typ = detect_call2go(text)
        # Depende se _is_narrative_mention pega
        # "milhões de streams" + "spotify" → NOT an exact narrative pattern
        # O fallback \bspotify\b vai pegar → texto_implicito
        assert has == 1  # O detector PEGA (isso pode ser um problema)

    def test_eric_land_mencao_narrativa_canal(self):
        """Caso Eric Land: canal tem menção narrativa, não Call2Go."""
        text = "Eric Land - 200 dias nos charts do Spotify"
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'

    def test_grupo_menos_e_mais_charts(self):
        """Caso Grupo Menos É Mais: '200 dias nos charts do Spotify'."""
        text = "Grupo Menos É Mais - 200 dias nos charts do Spotify"
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'

    def test_provided_to_youtube_com_link_spotify(self):
        """Vídeo auto-gerado mas COM link Spotify na descrição."""
        text = "Provided to YouTube by DistroKid\n\nhttps://open.spotify.com/track/abc"
        assert is_auto_generated(text) is True
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_descricao_curta_sem_nada(self):
        """Descrição curta típica de Shorts."""
        text = "#shorts #musica"
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'

    def test_descricao_vazia_shorts(self):
        """Descrição completamente vazia (Shorts/Reels)."""
        text = ""
        has, typ = detect_call2go(text)
        assert has == 0 and typ == 'nenhum'


# =====================================================================
# GRUPO 11: Falsos positivos conhecidos (documentar comportamento)
# =====================================================================

class TestFalsosPositivosConhecidos:
    """Documenta comportamento em casos que podem gerar falsos positivos.
    Estes testes NÃO são para quebrar — são para DOCUMENTAR o comportamento atual."""

    def test_fallback_spotify_generico(self):
        """Menção genérica 'Spotify' sem narrativa → fallback pega."""
        text = "Siga minha playlist no Spotify"
        has, typ = detect_call2go(text)
        # Fallback \bspotify\b + not narrative → texto_implicito
        assert has == 1 and typ == 'texto_implicito'

    def test_spotify_no_nome_da_playlist(self):
        """Nome de playlist mencionado → fallback pode pegar."""
        text = "Essa música está na playlist 'Melhores do Spotify'"
        has, typ = detect_call2go(text)
        # Não é narrativa padrão → fallback pega
        assert has == 1

    def test_mencionando_competidor(self):
        """Menção a Spotify como comparação → fallback pega."""
        text = "Melhor que o Spotify, ouça no Deezer"
        has, typ = detect_call2go(text)
        # \bspotify\b + not narrative → texto_implicito (falso positivo)
        assert has == 1


# =====================================================================
# GRUPO R6 — Deep links nativos do Spotify (Fase 18)
# =====================================================================

class TestR6DeepLinks:
    """Detecta deep links spotify:tipo:id que abrem o app Spotify diretamente."""

    def test_deep_link_artist(self):
        text = "Siga: spotify:artist:6eUKZXaKkcviH0Ku9w2n3V"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_deep_link_track(self):
        text = "Tocando agora: spotify:track:7ouMYWpwJ422jRcDASZB7P"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_deep_link_album(self):
        text = "Album completo: spotify:album:1DFixLWuPkv3KT3TnV35m3"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_deep_link_playlist(self):
        text = "Playlist oficial: spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_deep_link_id_curto_invalido(self):
        """ID muito curto (<8 chars) NAO deve casar (R6 exige 8+ chars)."""
        text = "spotify:artist:abc"
        has, typ = detect_call2go(text)
        # Cai no R5 fallback (\bspotify\b) → texto_implicito
        assert has == 1 and typ == 'texto_implicito'


# =====================================================================
# GRUPO R7 — Agregadores de redes sociais com referência a Spotify (Fase 18)
# =====================================================================

class TestR7Aggregators:
    """Detecta linktr.ee/foo/spotify, lnk.bio/.../spotify, etc."""

    def test_linktree_spotify(self):
        text = "Todas as plataformas: https://linktr.ee/maluma/spotify"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_lnk_bio_spotify(self):
        text = "Veja em https://lnk.bio/artist/spotify-link"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_beacons_ai_spotify(self):
        text = "Acesse: beacons.ai/artistname/spotify"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_allmylinks_spotify(self):
        text = "Links: https://allmylinks.com/artist/spotify-page"
        has, typ = detect_call2go(text)
        assert has == 1 and typ == 'link_direto'

    def test_aggregator_sem_spotify_no_path(self):
        """linktr.ee/x/y SEM spotify no path NAO casa o R7."""
        text = "Ver mais em https://linktr.ee/artistname/website"
        has, typ = detect_call2go(text)
        # nao deve detectar como Call2Go (sem spotify mencionado)
        assert has == 0


# =====================================================================
# GRUPO R8 — CTA com emoji musical próximo a "spotify" (Fase 18)
# =====================================================================

class TestR8EmojiCTA:
    """Detecta CTAs como '🎵 Ouca no Spotify', '🎧 Spotify aqui', etc."""

    def test_emoji_nota_musical(self):
        text = "🎵 Disponivel no Spotify agora!"
        has, typ = detect_call2go(text)
        assert has == 1
        # pode cair como texto_implicito ou link_direto dependendo da ordem

    def test_emoji_fone_de_ouvido(self):
        text = "🎧 Escute no Spotify"
        has, typ = detect_call2go(text)
        assert has == 1

    def test_emoji_microfone(self):
        text = "🎶 Spotify ja tem!"
        has, typ = detect_call2go(text)
        assert has == 1

    def test_emoji_distante_spotify(self):
        """Emoji muito distante (>60 chars) NAO casa R8."""
        text = (
            "🎵 Aqui vai a letra completa da musica que escrevi durante o "
            "verao em Salvador depois de muitas inspiracoes do Spotify"
        )
        # Distancia entre emoji e 'spotify' > 60 chars -- R8 nao casa
        # Mas R5 fallback ainda pode pegar
        has, typ = detect_call2go(text)
        assert has == 1  # via R5

    def test_emoji_sem_spotify(self):
        """Emoji sem mencao a Spotify -> nao detecta Call2Go."""
        text = "🎵 Que dia lindo para musica nova"
        has, typ = detect_call2go(text)
        assert has == 0


# =====================================================================
# GRUPO STRICT (heuristica de auto-gen rebaixar confianca, Fase 18)
# =====================================================================

class TestStrictHeuristic:
    """A coluna has_call2go_strict so e 1 quando ha link direto E nao auto-gerado.

    Esses testes nao podem ser feitos em detect_call2go() puro -- o strict e
    aplicado apenas no process_videos() que percorre o JSONL. Aqui apenas
    valida que is_auto_generated() segue funcionando.
    """

    def test_auto_gen_provided_to_youtube(self):
        text = "Provided to YouTube by Universal Music Group\n\nSong title - Artist"
        assert is_auto_generated(text) is True

    def test_auto_gen_youtube_generated(self):
        text = "Auto-generated by YouTube.\n\nMore details below"
        assert is_auto_generated(text) is True

    def test_organic_video(self):
        text = "Bem-vindo ao meu novo clipe! Ouca no Spotify"
        assert is_auto_generated(text) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
