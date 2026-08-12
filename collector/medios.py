# Sección 2.2 del plan madre. Medios internacionales: hay ratings públicos (AllSides,
# Media Bias/Fact Check), se usan tal cual. Medios chilenos: NO existen ratings públicos
# equivalentes — inventar izquierda/derecha sería opinión disfrazada de dato (regla dura
# en CLAUDE.md), así que se clasifica por propiedad y tradición editorial en su lugar.

LEAN_INTL = {
    "reuters.com": "centro",
    "apnews.com": "centro",
    "bloomberg.com": "centro",
    "ft.com": "centro",
    "cnbc.com": "centro",
    "bbc.co.uk": "centro",
    "wsj.com": "centro-derecha",
    "foxbusiness.com": "derecha",
    "nytimes.com": "centro-izquierda",
    "theguardian.com": "izquierda",
    "aljazeera.com": "sin-clasificar",
    "france24.com": "centro",
}

MEDIOS_CL = {
    "emol.com": {"grupo": "El Mercurio", "tipo": "tradicional"},
    "latercera.com": {"grupo": "Copesa", "tipo": "tradicional"},
    "df.cl": {"grupo": "Claro", "tipo": "económico"},
    "biobiochile.cl": {"grupo": "independiente", "tipo": "regional"},
    "elmostrador.cl": {"grupo": "independiente", "tipo": "digital"},
    "ex-ante.cl": {"grupo": "independiente", "tipo": "digital"},
    "ciperchile.cl": {"grupo": "sin fines de lucro", "tipo": "investigación"},
    "t13.cl": {"grupo": "Luksic", "tipo": "TV"},
    "24horas.cl": {"grupo": "TVN (público)", "tipo": "TV"},
    "cooperativa.cl": {"grupo": "independiente", "tipo": "radio"},
    "theclinic.cl": {"grupo": "independiente", "tipo": "digital"},
}


def resolver_medio(dominio: str, nombre_medio: str) -> dict:
    """Devuelve {medio, grupo, lean} para un artículo, según de qué tabla salga el
    dominio. Si el dominio no está en ninguna tabla, grupo/lean quedan "sin-clasificar" —
    nunca se inventa una clasificación política."""
    if dominio in LEAN_INTL:
        return {"medio": nombre_medio, "grupo": nombre_medio, "lean": LEAN_INTL[dominio]}
    if dominio in MEDIOS_CL:
        info = MEDIOS_CL[dominio]
        return {"medio": nombre_medio, "grupo": info["grupo"], "lean": "no aplica"}
    return {"medio": nombre_medio, "grupo": "sin-clasificar", "lean": "sin-clasificar"}
