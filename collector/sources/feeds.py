# Catálogo de feeds verificados a mano (curl real, sección 2.1 del plan madre). De los ~18
# candidatos que lista el plan madre, bastantes quedaron descartados por no tener RSS
# funcionando hoy — varios medios chilenos lo dejaron de mantener con los años. No se
# reemplazan por scraping de HTML (regla explícita del plan madre): si no hay RSS, se saca.
#
# Descartados y por qué: AP News (RSS discontinuado, DNS ni resuelve), Emol/BioBioChile/
# La Tercera/El Mostrador/T13/24 Horas/Cooperativa/La Segunda (sin feed RSS encontrado tras
# búsqueda razonable — sus URLs históricas devuelven HTML o 404).

# Cada entrada: (url, medio, dominio_para_lean)
# `dominio_para_lean` es la clave que se busca en collector.medios (LEAN_INTL/MEDIOS_CL) —
# a veces no coincide con el dominio real del feed (ej. FT News Briefing vive en acast.com
# pero es contenido editorial de FT).

FEEDS_MUNDO = [
    (
        "https://news.google.com/rss/search?q=site:reuters.com+when:1d&hl=en-US&gl=US&ceid=US:en",
        "Reuters",
        "reuters.com",
    ),
    ("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC", "bbc.co.uk"),
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera", "aljazeera.com"),
    ("https://www.france24.com/en/rss", "France24", "france24.com"),
    ("https://feeds.acast.com/public/shows/ftnewsbriefing", "Financial Times", "ft.com"),
]

FEEDS_CHILE = [
    ("https://www.df.cl/noticias/site/list/port/rss.xml", "Diario Financiero", "df.cl"),
    ("https://www.ex-ante.cl/feed/", "Ex-Ante", "ex-ante.cl"),
    ("https://www.ciperchile.cl/feed/", "CIPER", "ciperchile.cl"),
    ("https://www.theclinic.cl/feed/", "The Clinic", "theclinic.cl"),
]


def feed_noticias_ticker(ticker: str) -> str:
    # Yahoo usa guion para clases de acción (BRK-B), no el punto de la notación
    # habitual (BRK.B) que sí entienden Finnhub/EDGAR — sin este mapeo el feed
    # devuelve vacío para cualquier ticker con clase de acción.
    simbolo_yahoo = ticker.replace(".", "-")
    return f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={simbolo_yahoo}&region=US&lang=en-US"
