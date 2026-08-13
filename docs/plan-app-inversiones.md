# Plan: Dashboard de Inversiones y Actualidad

**Para:** Claude Code (WSL)
**Usuario:** José — estudiante de Ing. Civil Industrial, 4to año, Santiago. Portafolio real
pequeño (~US$150) en fase de aprendizaje. Sabe Python, no React. Claude Code es quien
escribe el código.
**Objetivo:** una URL que abre en el celular cada mañana. Ve qué pasó en el mundo, en Chile,
y con sus inversiones. Datos duros con fuente verificable. Cero costo de operación.

Las reglas duras del proyecto (EDGAR, Gemini, copyright, costo, diseño, radar, tesis) viven
en `CLAUDE.md`, no acá — este documento las referencia donde aplican en vez de repetirlas.

---

## 0. Arquitectura

### 0.1 Dos programas

```
┌──────────────────────────────────────────────┐
│  RECOLECTOR (Python)                         │
│  GitHub Actions · cron 07:00 America/Santiago│
│                                              │
│  1. Lee watchlist.txt                        │
│  2. RSS: mundo, Chile, actualidad, por ticker│
│  3. EDGAR: fundamentales de la watchlist     │
│  4. Precios: watchlist + referencias + radar │
│  5. Banco Central: UF, dólar, IPC, TPM       │
│  6. Gemini: agrupa historias, resume         │
│  7. Screener: corre el radar                 │
│  8. Escribe data/daily.json → commit → push  │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
          data/daily.json
                 │
                 ▼
┌──────────────────────────────────────────────┐
│  VISOR (React + Vite → Vercel)               │
│  Solo lee el JSON. Cero llamadas en vivo.    │
│  El push a data/ dispara redeploy automático.│
└──────────────────────────────────────────────┘
```

**Por qué separado:**
- El visor nunca espera a una API → abre instantáneo en el celular
- Si una fuente muere, el JSON de ayer sigue ahí (degrada, no se cae)
- El JSON versionado en git es historial gratis de todo lo que vio
- Vercel no duerme; Streamlit Cloud sí

### 0.2 Costos — todo free tier

| Servicio | Plan | Límite | Uso real |
|---|---|---|---|
| GitHub Actions (repo público) | Gratis | Ilimitado | ~4 min/día |
| Vercel | Hobby | 100GB banda | Nada |
| SEC EDGAR | Gratis, sin key | 10 req/seg | ~30/día |
| Banco Central de Chile | Gratis, con registro | — | ~4/día |
| Finnhub (precios) | Gratis | 60 req/min | ~150/día |
| RSS (todas las fuentes) | Gratis | — | ~50/día |
| Gemini 2.5 Flash API | Free tier | Ver Bug #8 del CRM | ~25/día |

**Total: $0/mes.**

Nota sobre Gemini: la API key de Google AI Studio tiene free tier **independiente** de la
suscripción de la app de Gemini. Si la suscripción se cae en noviembre, la app sigue
funcionando.

### 0.3 Degradación obligatoria

Cada componente falla solo, nunca en cascada:

| Si falla | Entonces |
|---|---|
| Una fuente RSS | Las demás siguen; se registra en `errores` |
| Gemini | Agrupación cae a método por keywords + dominio |
| EDGAR | Se usan los fundamentales cacheados del último filing |
| Finnhub | Precios del día anterior, marcados como desactualizados |
| Todo el recolector | El visor muestra el JSON de ayer con aviso de fecha |

---

## 1. Estructura de la pantalla

Orden vertical, columna única en móvil:

```
┌────────────────────────────────────────┐
│ Actualizado hoy 07:02                  │
├────────────────────────────────────────┤
│ ▓▓ MUNDO                               │
│   Historia agrupada, multi-fuente      │
│   Historia agrupada, multi-fuente      │
│   Historia agrupada, multi-fuente      │
├────────────────────────────────────────┤
│ ▓▓ CHILE                               │
│   Historia agrupada, multi-fuente      │
│   Historia agrupada, multi-fuente      │
├────────────────────────────────────────┤
│ ▓ ACTUALIDAD                (compacto) │
│   · Pakistán · Túnez · etc.            │
├────────────────────────────────────────┤
│ ▓▓ MIS INVERSIONES                     │
│ ┌────────────────────────────────────┐ │
│ │ MSFT      $504,47   +27,6%   ●verde│ │
│ │ ╭─────── gráfico precio ─────────╮ │ │
│ │ │                          ╱      │ │ │
│ │ ╰────────────────────────────────╯ │ │
│ │ · Azure supera expectativas   [FT] │ │
│ │ · Capex de IA bajo escrutinio [RTR]│ │
│ │                          [abrir ▾] │ │
│ └────────────────────────────────────┘ │
│   (una card por cada ticker)           │
├────────────────────────────────────────┤
│ ▓ REFERENCIAS                          │
│   VOO · QQQ · IPSA · UF · Dólar · TPM  │
├────────────────────────────────────────┤
│ ▓ EN EL RADAR                          │
│   Castigadas pero sanas                │
│   + descartadas, con el motivo         │
└────────────────────────────────────────┘
```

### 1.1 La card de inversión: colapsada vs. expandida

**Colapsada** (lo que ve al abrir):
- Ticker, precio, variación del día, variación desde su costo medio
- Semáforo de tesis
- Gráfico de precio (línea simple, 1 año por defecto)
- 2-3 titulares en una línea cada uno, con el medio entre corchetes

**Expandida** (al tocar "abrir"):
- Selector de rango del gráfico: 1M / 6M / 1A / 5A
- **Tabla de fundamentales** (la densidad tipo TIKR):

  | | Actual | Año ant. | Var |
  |---|---|---|---|
  | Ingresos | $90.007M | $76.441M | +18% |
  | Operating income | $40.603M | $34.418M | +18% |
  | EPS diluido (GAAP) | $4,81 | $3,46 | +39% |
  | EPS (non-GAAP) | $4,74 | $3,55 | +34% |
  | Margen operativo | 45,1% | 45,0% | +0,1pp |
  | Capex | $35.802M | $17.098M | +109% |
  | Flujo operativo | $47.318M | $37.196M | +27% |
  | Capex / Flujo op. | 75,7% | 46,0% | +29,7pp |

  Serie histórica de 12 trimestres para cada fila, en tabla, no en gráfico.

- **Segmentos** con crecimiento (Intelligent Cloud +32%, Azure +43%, etc.)
- **Noticias completas**: titular, extracto de 1-2 frases, medio con su lean, link
- Próxima fecha de earnings
- Tesis escrita con umbrales y estado

**Regla de la card:** colapsada responde "¿pasó algo?". Expandida responde "¿por qué y qué
significa?". Si un dato no ayuda a ninguna de las dos, no va.

---

## 2. Fuentes

### 2.1 Noticias — todo por RSS, gratis, sin key

**Mundo:**
```
Reuters World      → vía Google News RSS si el directo falla
AP News            → https://feeds.apnews.com/rss/apf-topnews
BBC World          → https://feeds.bbci.co.uk/news/world/rss.xml
Al Jazeera         → https://www.aljazeera.com/xml/rss/all.xml
France24 (inglés)  → https://www.france24.com/en/rss
FT News Briefing   → feed del podcast; el <description> trae los temas del día
```

**Chile:**
```
Emol               BioBioChile        La Tercera
El Mostrador       Ex-Ante            CIPER
T13                24 Horas           Cooperativa
Diario Financiero  La Segunda         The Clinic
```
Buscar el feed RSS de cada uno. Los que no tengan, sacarlos — no scrapear HTML, es frágil
y se rompe solo.

Primer Click: buscar feed del podcast. Verificar que el `<description>` traiga temas útiles
antes de construir encima. Si viene vacío, descartar sin drama — los feeds de arriba cubren
lo mismo.

**Actualidad (bloque compacto):** mismos feeds internacionales, pero filtrando lo que **no**
es economía ni Chile. Es el bloque de "qué está pasando en el mundo que debería saber".
Máximo 5 items, una línea cada uno.

**Por inversión:**
```
https://feeds.finance.yahoo.com/rss/2.0/headline?s={TICKER}&region=US&lang=en-US
```
Respaldo: endpoint `company-news` de Finnhub.

### 2.2 Sesgo de fuentes — el mecanismo Ground News

Lo valioso de Ground News no es la noticia, es mostrar quién cubrió y desde dónde. Eso se
replica: agrupar la misma historia de varios medios y etiquetar cada medio.

**Medios internacionales** — hay ratings públicos (AllSides, Media Bias/Fact Check):

```python
LEAN_INTL = {
    "reuters.com":     "centro",
    "apnews.com":      "centro",
    "bloomberg.com":   "centro",
    "ft.com":          "centro",
    "cnbc.com":        "centro",
    "bbc.co.uk":       "centro",
    "wsj.com":         "centro-derecha",
    "foxbusiness.com": "derecha",
    "nytimes.com":     "centro-izquierda",
    "theguardian.com": "izquierda",
    "aljazeera.com":   "sin-clasificar",
}
```

**Medios chilenos** — acá NO existen ratings publicados equivalentes. Inventar etiquetas
izquierda/derecha sería opinión disfrazada de dato. En vez de eso se clasifica por
**propiedad y tradición editorial**, que es información pública y verificable:

```python
MEDIOS_CL = {
    "emol.com":            {"grupo": "El Mercurio",     "tipo": "tradicional"},
    "latercera.com":       {"grupo": "Copesa",          "tipo": "tradicional"},
    "df.cl":               {"grupo": "Claro",           "tipo": "económico"},
    "biobiochile.cl":      {"grupo": "independiente",   "tipo": "regional"},
    "elmostrador.cl":      {"grupo": "independiente",   "tipo": "digital"},
    "ex-ante.cl":          {"grupo": "independiente",   "tipo": "digital"},
    "ciperchile.cl":       {"grupo": "sin fines de lucro", "tipo": "investigación"},
    "t13.cl":              {"grupo": "Luksic",          "tipo": "TV"},
    "24horas.cl":          {"grupo": "TVN (público)",   "tipo": "TV"},
    "cooperativa.cl":      {"grupo": "independiente",   "tipo": "radio"},
    "theclinic.cl":        {"grupo": "independiente",   "tipo": "digital"},
}
```

En la UI se muestra el grupo, no una etiqueta política. El usuario ve *quién* publicó y de
*quién* es ese medio, y saca sus propias conclusiones. Campo editable — si quiere agregar
su propia clasificación, edita el diccionario.

**Señal importante:** cuando una historia la cubre un solo grupo o un solo lean, marcarlo
visiblemente. Esa es la información más útil de todo el bloque.

**Agrupación con Gemini** — JSON estricto:

```
Agrupa estos titulares por historia. Dos titulares son la misma historia si
se refieren al mismo hecho concreto.

Responde SOLO JSON, sin markdown:
{
  "historias": [
    {
      "titulo_neutral": "<descripción factual del hecho, sin adjetivos>",
      "indices": [0, 3, 7]
    }
  ]
}

No inventes historias que no estén en la lista. No agrupes por tema general,
solo por hecho específico.
```

Fallback sin LLM: agrupar por solapamiento de sustantivos propios en los titulares.
Peor, pero funciona.

**Mecanismo real de la API (verificado a mano contra la API real con key real, 2026-08-13)**
— el endpoint clásico `models/{modelo}:generateContent` está **deprecado para cuentas
nuevas** (devuelve 404 "no longer available to new users", recomienda migrar a la API de
Interactions). Lo que sí funciona hoy:

```
POST https://generativelanguage.googleapis.com/v1beta/interactions
Header: x-goog-api-key: <GEMINI_API_KEY>   (no ?key= por query param)

Body:
{
  "model": "gemini-flash-lite-latest",
  "input": "<prompt>",
  "response_format": {
    "type": "text",
    "mime_type": "application/json",
    "schema": { ... JSON Schema ... }
  }
}
```

La respuesta trae `status: "completed"` y una lista `steps` — el texto generado está en el
`step` con `type: "model_output"`, dentro de `content[].text` (parsear como JSON). Se probó
`gemini-flash-lite-latest` contra `gemini-flash-latest`/`gemini-3.6-flash`: misma calidad de
resultado en tareas de clasificación/reescritura simples, pero `gemini-flash-lite-latest` usa
0 tokens de "pensamiento" (los otros gastan cientos por default) — mismo tier gratis, más
barato. Implementado en `collector/sources/gemini.py`.

### 2.3 Fundamentales — SEC EDGAR

- Base: `https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json`
- Índice de filings: `https://data.sec.gov/submissions/CIK{cik}.json`
- **`User-Agent` real obligatorio** — regla dura completa en `CLAUDE.md`. Esta es la trampa
  #1 del proyecto.
- Rate limit 10 req/seg
- Cache agresivo: los fundamentales cambian 4 veces al año. Guardar el `accessionNumber`
  del último filing procesado y no volver a pegar si no cambió.

Tags:

| Dato | Tag `us-gaap` |
|---|---|
| Ingresos | `RevenueFromContractWithCustomerExcludingAssessedTax` |
| Operating income | `OperatingIncomeLoss` |
| Net income | `NetIncomeLoss` |
| EPS diluido | `EarningsPerShareDiluted` |
| Capex | `PaymentsToAcquirePropertyPlantAndEquipment` |
| Flujo operativo | `NetCashProvidedByUsedInOperatingActivities` |
| Patrimonio | `StockholdersEquity` |
| Deuda | `LongTermDebtNoncurrent` |

CIKs: MSFT `0000789019` · MCD `0000063908` · BRK.B `0001067983` · AAPL `0000320193`

**Segmentos** (Azure +43%, comparable sales de MCD): no están en XBRL. Viven en prosa
dentro del 8-K Exhibit 99.1. Extracción con Gemini — regla dura de validación de cita
completa en `CLAUDE.md`.

### 2.4 Precios — Finnhub para el presente, Yahoo Finance para sembrar el pasado

- Cotización de hoy: endpoint `quote` de Finnhub, gratis. 60 req/min — con ~90 tickers
  (watchlist + referencias + universo del radar) alcanza de sobra si se serializa.
- **`stock/candle` (histórico) NO es gratis** — Finnhub lo movió a planes pagos, confirmado
  contra `github.com/finnhubio/Finnhub-API` issues #546 y #397 (403 real probado en Fase 1).
  El plan original acá asumía que era gratis; no lo es.
- Histórico para sembrar el gráfico: endpoint no oficial de gráficos de Yahoo Finance
  (`query1.finance.yahoo.com/v8/finance/chart/{ticker}`, mismo que usa la librería
  `yfinance`), sin key. Se usa **una sola vez por ticker**, para sembrar
  `data/historico_precios.json` — nunca en la corrida de siempre, así que si Yahoo cambia o
  bloquea el endpoint algún día, solo se rompe sembrar un ticker *nuevo*, no el pipeline
  diario. Desde ahí, cada corrida de Finnhub le suma un punto más al historial acumulado
  (ver `collector/historico.py`).

### 2.5 Chile macro — Banco Central

API de la Base de Datos Estadísticos (BDE). Requiere registro en
[si3.bcentral.cl/Siete](https://si3.bcentral.cl/Siete), es gratis. El portal se rediseñó en
algún momento de 2024+: **ya no es usuario/contraseña por query params** (eso queda para el
servicio SOAP viejo, que no se usa acá) — es un token único, `BCCH_API_KEY`, que se copia
desde "API BDE" → "Acceso a la API" una vez logueado y con el servicio activado.

Endpoint: `https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?token=...&function=GetSeries&timeseries=CODIGO&firstdate=YYYY-MM-DD&lastdate=YYYY-MM-DD`.
**La respuesta viene en `latin-1`, no UTF-8** — decodificarla como UTF-8 revienta.

Códigos verificados contra la API real (no adivinados — algunos no se encuentran por texto
libre en `SearchSeries`, hubo que buscarlos a mano en el buscador del portal):

| Dato | Código | Frecuencia |
|---|---|---|
| UF | `F073.UFF.PRE.Z.D` | Diaria |
| Dólar observado | `F073.TCO.PRE.Z.D` | Diaria |
| TPM | `F022.TPM.TIN.D001.NO.Z.D` | Diaria |
| IPC (variación 12 meses) | `G073.IPC.V12.2023.M` | Mensual |
| IPSA | `F013.IBC.IND.N.7.LAC.CL.CLP.BLO.M` | Mensual |

Las series mensuales solo tienen una observación al mes — pedir con una ventana de días
corta (se probó con 10) puede dejar la última observación fuera de rango y devolver "sin
dato" en silencio. `collector/sources/banco_central.py` usa una ventana de 45 días para
evitar justo eso (pasó de verdad en una corrida real: IPSA e IPC volvían el valor inventado
de Fase 0 en vez de fallar audiblemente).

Van al bloque de Referencias, no a una card propia.

### 2.6 Copyright

Regla dura completa en `CLAUDE.md` (agregar, no republicar; máximo 1-2 frases; resúmenes
reescritos, no recortes; link siempre visible).

---

## 3. El Radar

### 3.1 Qué es

Empresas castigadas en precio **pero sanas en fundamentales**. Es la distinción entre bache
temporal y deterioro estructural — Microsoft en junio 2026 habría aparecido; Ubisoft no.

**No es una recomendación de compra** — regla dura completa en `CLAUDE.md`. Muestra
candidatos con sus datos; la decisión y la tesis son del usuario.

### 3.2 Universo (~90 tickers, refrescado semanal)

**Grandes conocidas (~50):** componentes principales del S&P 100.

**ADRs chilenos (~6):** `BCH` Banco de Chile · `BSAC` Santander Chile · `SQM` ·
`ENIC` Enel Chile · `CCU` · `LTM` LATAM.

> Las acciones del IPSA no se compran desde su app (opera papeles listados en EEUU). Los
> ADRs sí. Por eso el universo usa ADRs y no tickers del IPSA.

**Sectores de interés (~25):**
- Gaming: `EA` `TTWO` `RBLX` `NTDOY` `UBSFY` `SONY`
- Autos / JDM: `TM` Toyota · `HMC` Honda · `F` · `GM` · `STLA` · `RACE`
- Tech: `AAPL` `GOOGL` `AMZN` `NVDA` `META` `AMD` `INTC` `CRM` `ORCL`
- Bancos: `JPM` `BAC` `GS`

**ETFs de referencia (no entran al radar, van a Referencias):** `VOO` S&P 500 ·
`QQQ` Nasdaq-100 · `VTI` mercado total EEUU.

### 3.3 Criterios

**Castigada** (al menos uno):
- Precio bajo el 85% de su máximo de 52 semanas
- Precio bajo su promedio móvil de 200 días

**Sana** (todos obligatorios):
- Crecimiento de ingresos YoY positivo
- Margen operativo positivo
- Ingresos creciendo en al menos 3 de los últimos 4 trimestres
- Flujo operativo positivo
- Deuda / patrimonio menor a 2 (excepción: bancos, donde no aplica)

### 3.4 El descarte visible

**Esta es la mitad del valor del bloque.** Toda empresa castigada que NO pase el filtro
aparece igual, en una lista secundaria, con el motivo:

> **UBSFY** — 62% bajo su máximo. Descartada: margen operativo negativo, ingresos cayendo
> 4 de los últimos 4 trimestres.

> **INTC** — 31% bajo su máximo. Descartada: flujo operativo negativo.

Ver por qué algo no califica enseña más que ver la lista de aprobados. Es el filtro que le
faltaba al usuario cuando comparaba Apple con Ubisoft.

### 3.5 Puerta de entrada

Si toca "invertir" desde una card del radar, la UI le pide escribir la tesis antes de darle
el link al broker: qué cree que va a pasar en el negocio, y qué número lo haría admitir que
se equivocó. Se guarda en la hoja de tesis (ver `spec-rastreador-tesis.md`).

Sin tesis escrita, no hay link. Es el único punto donde la app le pone fricción a propósito.

---

## 4. Diseño

### 4.1 Tensión a resolver

Pidió densidad tipo TIKR **y** que se vea bien. Se resuelve con una regla dura:
**el color es solo señal.**

Esta app es un instrumento de lectura, no un terminal de trading. Todo el proyecto empuja
en la misma dirección: bajar la velocidad, ir a la fuente, revisar la tesis. El diseño tiene
que apoyar eso, no simular una sala de operaciones.

> **Excepción explícita (decidida por el usuario, 2026-08-11):** el recolector corre cada
> hora, todo el día (`.github/workflows/daily.yml`), no una vez a las 7am como se pensó acá
> originalmente. Se le señaló la tensión con este párrafo antes de decidirlo — no se coló
> "ya que estamos automatizando". La sección 10 sigue siendo la vara para medir si la app
> cumplió su propósito, independiente de cada cuánto se actualiza el dato.

### 4.2 Tokens

```css
/* Base — todo lo que no es señal vive acá */
--tinta:        #14171C;   /* texto principal */
--tinta-media:  #3D434D;   /* texto secundario */
--tinta-suave:  #6B7280;   /* labels, metadata */
--papel:        #FAFAF8;   /* fondo */
--papel-hueco:  #F1F1EE;   /* cards, divisores */
--linea:        #DEDEDA;   /* bordes */

/* Señal — solo para estado, nunca decorativo */
--verde:        #1F7A4D;   /* tesis intacta, radar aprobado */
--ambar:        #B87407;   /* revisar */
--rojo:         #B03A2E;   /* tesis rota, radar descartado */
--acento:       #2B4C7E;   /* links y foco. UN solo acento */
```

Si un elemento no comunica estado, va en escala de grises. Sin excepciones. Eso es lo que
permite que un dashboard denso siga siendo legible: cuando aparece color, importa.

Modo oscuro: invertir la escala tinta/papel, mantener los mismos valores de señal.

### 4.3 Tipografía

Una sola familia, diferenciada por ancho y peso. Da cohesión de instrumento y evita el look
de plantilla:

- **Cifras y tablas:** IBM Plex Mono — cifras tabulares reales, las columnas se alinean solas
- **Cuerpo e interfaz:** IBM Plex Sans — buen soporte de acentos en español
- **Títulos de sección:** IBM Plex Sans Condensed, peso 600, tracking cerrado

Escala: 12 / 14 / 16 / 20 / 28 / 40. Nada intermedio.

### 4.4 Elemento firma

**Ningún número aparece sin su fuente.**

Cada cifra es tappeable y despliega de dónde salió, la frase textual del documento original,
y el link. El 43% de Azure muestra la oración del press release donde lo dice.

Componente `<Cifra valor fuente cita url />`. Si le falta la fuente, renderiza en gris con
marcador de "sin verificar" — que se note.

Esto es lo que separa la app de otro dashboard más: es un instrumento de aprendizaje. TIKR
te muestra el número; esto te muestra el número y de dónde salió.

### 4.5 Piso de calidad

- Responsive real desde 360px
- Foco de teclado visible
- `prefers-reduced-motion` respetado
- Estado vacío que dice qué hacer, no "no hay datos"
- Estado de error que dice qué falló y cómo arreglarlo
- El bloque `errores` del JSON se muestra al pie, discreto pero visible

### 4.6 Gráficos

Solo precio en el tiempo. Recharts, línea simple con relleno degradado sutil bajo la línea
(usando `--acento`, excepción explícita — ver `CLAUDE.md`), sin puntos salvo el punto activo
al pasar el mouse (viene gratis con el tooltip de Recharts). Rangos 1M / 6M / 1A / 5A. Eje Y
con cifras tabulares.

Velas (candlestick): descartadas por ahora — necesitan datos OHLC que no existen en el
modelo todavía (Finnhub los trae recién en Fase 1) y Recharts no las trae nativas, hay que
armarlas a mano. Se reevalúa más adelante, una vez que haya datos reales de precio.

Los fundamentales van en tabla, no en gráfico. Doce trimestres en columnas se leen mejor
que doce gráficos.

---

## 5. Modelo de datos

```json
{
  "generado": "2026-08-11T07:02:00-04:00",
  "errores": ["primer_click: feed sin respuesta"],

  "bloques": {
    "mundo":      [ /* historias */ ],
    "chile":      [ /* historias */ ],
    "actualidad": [ /* items simples, máx 5 */ ]
  },

  "posiciones": [
    {
      "ticker": "MSFT",
      "nombre": "Microsoft Corporation",
      "precio": 504.47,
      "var_dia_pct": 0.62,
      "var_ano_pct": -3.43,
      "serie_precio": { "1M": [...], "6M": [...], "1A": [...], "5A": [...] },
      "proxima_earnings": "2026-10-28",
      "fundamentales": {
        "periodo": "FY26Q4",
        "fuente_url": "https://www.sec.gov/...",
        "series": {
          "ingresos_musd":     [{"periodo": "FY26Q4", "valor": 90007}, ...],
          "op_income_musd":    [...],
          "eps_gaap":          [...],
          "eps_non_gaap":      [...],
          "margen_operativo":  [...],
          "capex_musd":        [...],
          "flujo_op_musd":     [...]
        }
      },
      "segmentos": [
        {
          "nombre": "Intelligent Cloud",
          "ingresos_musd": 39306,
          "var_pct": 32,
          "cita": "Revenue in Intelligent Cloud was $39.3 billion and increased 32%",
          "detalle": [
            {"nombre": "Azure", "var_pct": 43,
             "cita": "Azure and other cloud services revenue increased 43%"}
          ]
        }
      ],
      "tesis": {
        "texto": "El lock-in enterprise sostiene el crecimiento de Azure",
        "metrica": "Azure growth",
        "valor_actual": 43,
        "umbral_verde": 40,
        "umbral_rojo": 30,
        "semaforo": "verde"
      },
      "noticias": [ /* artículos */ ]
    }
  ],

  "referencias": {
    "indices": [
      {"ticker": "VOO", "nombre": "S&P 500", "precio": 0, "var_dia_pct": 0},
      {"ticker": "QQQ", "nombre": "Nasdaq-100", "precio": 0, "var_dia_pct": 0}
    ],
    "chile": {
      "ipsa": 0, "uf": 0, "dolar": 0, "tpm": 0, "ipc_12m": 0,
      "fuente": "Banco Central de Chile"
    }
  },

  "radar": {
    "candidatos": [
      {
        "ticker": "XXXX",
        "nombre": "...",
        "pct_bajo_maximo": 22,
        "motivo": "Ingresos +14% YoY, margen operativo 28%, flujo operativo positivo",
        "metricas": { "ingresos_var_pct": 14, "margen_op": 28, "deuda_patrimonio": 0.6 }
      }
    ],
    "descartados": [
      {
        "ticker": "UBSFY",
        "pct_bajo_maximo": 62,
        "motivo_descarte": "Margen operativo negativo; ingresos cayendo 4 de 4 trimestres"
      }
    ],
    "ultima_corrida": "2026-08-09"
  }
}
```

Estructura de un artículo:
```json
{
  "titular": "...",
  "extracto": "máximo 2 frases",
  "medio": "Reuters",
  "grupo": "independiente",
  "lean": "centro",
  "url": "https://...",
  "fecha": "2026-08-11T04:12:00Z"
}
```

Estructura de una historia agrupada:
```json
{
  "titulo_neutral": "...",
  "resumen": "reescrito, no recortado",
  "articulos": [ /* artículos */ ],
  "leans_presentes": ["centro", "centro-derecha"],
  "grupos_presentes": ["El Mercurio", "independiente"],
  "cobertura_unilateral": false
}
```

---

## 6. Fases

Cada fase termina en algo que funciona y se puede abrir. Los ▸ marcan puntos de corte
naturales dentro de una fase — se puede parar ahí sin dejar nada a medias.

### Estado actual (actualizar cada vez que se cierre o avance una fase)

- **Fase 0 — ✅ completa**, deployada en Vercel, verificada en el celular.
- **Fase 1 — ✅ completa.** `watchlist.txt` + parser + panel de edición desde el celular
  (excepción de auth, ver más abajo); cliente Finnhub (`/quote`, cotización — el histórico
  `/stock/candle` resultó de pago, se reemplazó por Yahoo Finance para sembrar el historial
  una sola vez, ver sección 2.4); `historico_precios.json` acumulado + `posiciones` reales en
  `daily.json`; Banco Central real (`collector/sources/banco_central.py`, token nuevo del
  portal rediseñado — ver sección 2.5) + índices de referencia reales (VOO/QQQ/VTI, mismo
  cliente Finnhub); GitHub Action corriendo **cada hora** (no solo `workflow_dispatch` —
  excepción consciente, ver sección 4.1).
- **Fase 2 — ✅ completa.** `mundo`/`chile`/`actualidad` con noticias reales por RSS, capadas
  a 8/8/5 (`collector/noticias.py`), noticias reales por ticker. De los ~18 feeds candidatos
  de la sección 2.1 solo 9 tienen RSS funcionando hoy — catálogo real en
  `collector/sources/feeds.py`. `extracto`/`resumen` quedan vacíos a propósito hasta Fase 3
  (sin Gemini no hay cómo reescribirlos sin copiar, regla dura de copyright).
- **Fase 3 — ✅ completa.** Agrupación real por historia vía Gemini (`collector/sources/
  gemini.py`) con fallback por keywords si no hay key o la llamada falla; `resumen` por
  historia y `extracto` por artículo (noticias por ticker) reescritos por Gemini, con chequeo
  de copia literal en código (`_es_copia_literal`, regla dura de copyright aplicada de forma
  verificable, no solo confiando en el prompt). `cobertura_unilateral` calculado de verdad.
  Ver sección 2.2 para el mecanismo real de la API (cambió respecto a lo documentado antes).
  Nota sobre Reuters vía Google News RSS (workaround del 403 directo, Fase 2): su `summary`
  no es un extracto real, es el titular envuelto en un tag `<a>` (más un `<font>Reuters</font>`)
  — Gemini logra extraer el texto del link y armar un resumen igual, pero se observó
  inconsistencia entre corridas (una corrida de prueba local dejó todo `mundo` sin resumen,
  la corrida real siguiente en producción sí los tuvo todos). No se investigó la causa exacta
  de la inconsistencia — anotar si se repite.
- **Fase 4 — ✅ completa.** Cliente EDGAR aislado (`collector/sources/edgar.py`), probado en
  vivo contra el CIK de MSFT antes de integrarlo — devuelve el FY26Q4 correcto. Dos hallazgos
  reales al probar contra datos reales, no anticipados por el plan: XBRL no trae el trimestre
  discreto (cada 10-Q tagea el acumulado year-to-date, el 10-K solo el año fiscal completo —
  Q4 se deriva restando año completo menos 9 meses) y un mismo período se repite en 2-3
  filings posteriores como comparativo con un `fy` distinto cada vez (la etiqueta sale del
  duplicado más antiguo, el valor del más nuevo). Fallback de tags por campo (MCD tagea
  ingresos como `Revenues`, no `RevenueFromContractWithCustomer...`) y chequeo de que el tag
  tenga datos recientes antes de aceptarlo — BRK.B no tagea EPS en XBRL desde 2013 ni tiene
  operating income reciente, esos campos quedan vacíos en vez de mostrar datos viejos.
  `eps_non_gaap` (columna que ya existía en `Fundamentales.series`) queda vacío a propósito:
  no es un tag XBRL estándar, es una cifra que cada empresa define en prosa en su press
  release — le toca a Fase 5. Cache por `accessionNumber` verificado (no repega si no cambió
  el filing). Conectado a `construir_posiciones()` en `main.py` con el mismo criterio de
  degradación que Banco Central/índices (si EDGAR falla, se conserva el valor anterior).
- **Fase 5 a 8 — ⬜ no iniciadas.**

### Fase 0 — Esqueleto que se ve

- Repo con `collector/` y `web/`
- `data/daily.json` escrito **a mano**, datos falsos pero realistas, cubriendo todos los
  bloques
- ▸ *corte*
- Vite + React + tokens de diseño, layout completo con los datos falsos
- Cards colapsables funcionando
- ▸ *corte*
- Deploy en Vercel

**Termina cuando:** abre una URL en el celular, ve el dashboard completo con datos
inventados, y se ve bien.

Hacer esto primero significa que el diseño se resuelve antes de que haya complejidad de
datos encima. Es la fase que más tienta saltarse y la que más ahorra después.

### Fase 1 — Watchlist, precios y referencias

- `watchlist.txt` + parser
- Cliente Finnhub: cotización y velas
- ▸ *corte*
- Banco Central: UF, dólar, TPM, IPC
- Sección `posiciones` y `referencias` del JSON
- ▸ *corte*
- GitHub Action con `workflow_dispatch` para probar a mano

**Termina cuando:** cambia `watchlist.txt`, pushea, y mañana aparecen los tickers nuevos.

> Editar la watchlist es un commit. Es una decisión mensual, no diaria — en general no
> vale construir autenticación y formularios de escritura para eso.
>
> **Excepción explícita:** se construyó igual un panel de edición desde el celular
> (`web/api/watchlist.ts` + panel en "Mis inversiones"), a pedido puntual del usuario, con
> una clave compartida en vez de login real — no autenticación completa, sigue siendo una
> app de un solo usuario. Ver `CLAUDE.md` para el detalle de los secrets involucrados.

### Fase 2 — Noticias

- Lector RSS, un módulo por fuente, try/except propio
- ▸ *corte*
- Feeds de mundo
- Feeds de Chile
- ▸ *corte*
- Filtro de actualidad (lo que no es economía ni Chile)
- Noticias por ticker
- Deduplicación por URL

**Termina cuando:** los tres bloques muestran noticias reales del día con link.

### Fase 3 — Agrupación y procedencia

- Tablas `LEAN_INTL` y `MEDIOS_CL`
- ▸ *corte*
- Agrupación con Gemini + JSON estricto
- Fallback por keywords
- ▸ *corte*
- Marcador de cobertura unilateral
- Resúmenes reescritos

**Termina cuando:** ve una historia con 4 medios de 3 procedencias distintas en una card.

### Fase 4 — Fundamentales EDGAR

- Cliente EDGAR aislado, `User-Agent` correcto, probado contra CIK de MSFT
- ▸ *corte* ← **no seguir hasta que esto devuelva el FY26Q4 correcto**
- Extracción XBRL de las 8 métricas, 12 trimestres
- Cache por `accessionNumber`
- ▸ *corte*
- Tabla de fundamentales en la card expandida
- Componente `<Cifra>` con fuente

**Termina cuando:** toca un número y ve de dónde salió.

### Fase 5 — Segmentos vía press release

- Detección de 8-K con Exhibit 99.1
- Extracción con Gemini
- **Validación de cita literal** — si la frase no existe en el documento, se descarta

**Termina cuando:** el 43% de Azure aparece con su oración textual.

### Fase 6 — Radar

- Universo fijo en un archivo
- ▸ *corte*
- Criterios de castigada y sana
- Lista de candidatos
- ▸ *corte*
- Lista de descartados con motivo
- Puerta de tesis antes del link al broker

**Termina cuando:** aparece al menos una descartada con un motivo que se entiende solo.

### Fase 7 — Tesis

Integrar `spec-rastreador-tesis.md`. Ya está diseñado, solo se conecta.

### Fase 8 — Pulido visual

Con Playwright MCP:
1. Screenshot en 360px y 1440px
2. Criticar contra la sección 4
3. Corregir una cosa
4. Repetir

Cortar cuando dos vueltas seguidas no encuentren nada real. El loop tiende a inventar
problemas para justificarse.

---

## 7. Repo

```
inversiones/
├── .github/workflows/
│   └── daily.yml
├── collector/
│   ├── main.py
│   ├── watchlist.py
│   ├── models.py
│   ├── sources/
│   │   ├── rss.py
│   │   ├── feeds.py           # catálogo de feeds por bloque
│   │   ├── edgar.py
│   │   ├── prices.py
│   │   └── banco_central.py
│   ├── enrich/
│   │   ├── grouping.py        # Gemini + fallback
│   │   └── extraction.py      # press release → segmentos
│   ├── radar/
│   │   ├── universo.py
│   │   └── screener.py
│   └── medios.py              # LEAN_INTL + MEDIOS_CL
├── data/
│   └── daily.json
├── web/
│   ├── src/
│   │   ├── tokens.css
│   │   ├── components/
│   │   │   ├── Cifra.tsx
│   │   │   ├── Semaforo.tsx
│   │   │   ├── Historia.tsx
│   │   │   ├── CardInversion.tsx
│   │   │   ├── GraficoPrecio.tsx
│   │   │   ├── TablaFundamentales.tsx
│   │   │   └── Radar.tsx
│   │   └── App.tsx
│   └── package.json
├── watchlist.txt
└── README.md
```

---

## 8. GitHub Action

El workflow real vive en `.github/workflows/daily.yml` — no se duplica acá para no
desincronizarse (mismo criterio que las reglas duras en `CLAUDE.md`). Corre cada hora, todo
el día, no una vez a las 7am como decía la versión original de esta sección — ver la
excepción documentada en la sección 4.1. Requiere permisos de escritura del `GITHUB_TOKEN`
(Settings → Actions → General → Workflow permissions → "Read and write permissions"), sin
eso el `git push` final falla con 403 — ver sección 9, Trampas conocidas.

Forma general, por si el archivo no está a mano:

```yaml
on:
  schedule:
    - cron: '0 * * * *'
  workflow_dispatch:

jobs:
  recolectar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: '3.12'
      - run: pip install -r collector/requirements.txt
      - run: python collector/main.py
        env:
          GEMINI_API_KEY:  ${{ secrets.GEMINI_API_KEY }}
          FINNHUB_KEY:     ${{ secrets.FINNHUB_KEY }}
          SEC_USER_AGENT:  ${{ secrets.SEC_USER_AGENT }}
          BCCH_USER:       ${{ secrets.BCCH_USER }}
          BCCH_PASS:       ${{ secrets.BCCH_PASS }}
      - run: |
          git config user.name "recolector"
          git config user.email "bot@users.noreply.github.com"
          git add data/daily.json
          git diff --staged --quiet || git commit -m "data: $(date +%F)"
          git push
```

El radar corre solo los lunes: agregar un chequeo de día en `main.py`.

Keys en GitHub Secrets, nunca en el código. Mismo criterio que `get_secret()` en el CRM.

---

## 9. Trampas conocidas

| Trampa | Por qué pasa | Salida |
|---|---|---|
| EDGAR 403 | `User-Agent` sin nombre/email real | Probar el cliente aislado antes de integrar |
| Gemini inventa cifras | Se le pide interpretar en vez de extraer | Validar que la cita exista literal |
| RSS de podcast vacío | Muchos no ponen show notes útiles | Verificar antes de construir encima |
| Feeds chilenos caídos | Varios medios cambian sus URLs de RSS | Un módulo por fuente, falla aislada |
| Cron no corre | GitHub pausa Actions en repos sin actividad | Commitear algo cada tanto |
| Todo se ve gris | Regla "color es señal" aplicada de más | Semáforo, leans y radar SÍ llevan color |
| Radar quema el free tier | Escanear 90 tickers a diario | Correrlo semanal, no diario |
| Scope infinito | Cada fase invita a una más | Cerrar la fase antes de abrir la siguiente |
| Finnhub `stock/candle` 403 | Lo movieron a plan pago, `quote` sigue gratis | Ver sección 2.4 — Yahoo Finance para sembrar una vez |
| Stooq CSV no responde con datos | Challenge JS anti-bots delante del endpoint | Se descartó; usar Yahoo Finance en su lugar |
| GitHub Action falla al hacer `git push` (403) | El `GITHUB_TOKEN` por defecto es read-only | Settings → Actions → General → Workflow permissions → "Read and write permissions". No es nada del código — se pierde tiempo si se busca ahí primero |
| Env var nueva "funciona" local pero se queda con datos viejos en producción | Falta mapear `secrets.X` en `.github/workflows/daily.yml` y/o crear el secret en GitHub — la degradación silenciosa (conservar el valor anterior) tapa el problema, no tira error | `gh secret list` para confirmar que el secret existe, y revisar el `env:` del workflow, antes de dar la fase por cerrada |
| Gemini `generateContent` devuelve 404 | Endpoint clásico deprecado para cuentas nuevas, migró a la API de Interactions | Usar `v1beta/interactions`, header `x-goog-api-key`, ver sección 2.2 |
| Historias de `mundo` sin `resumen` (a veces) | Reuters vía Google News RSS: `summary` es el titular envuelto en HTML, no un extracto real — Gemini a veces lo aprovecha igual, a veces no (inconsistente entre corridas, causa no confirmada) | Si se repite seguido, investigar; una corrida sin resumen no es necesariamente un bug |

---

## 10. Cómo saber si funcionó

No es que esté deployado ni que se vea bien.

Es que a los dos meses pueda mirar una tesis vieja, ver el semáforo en rojo, y acordarse de
que él escribió ese umbral antes de conocer el resultado.

Y que cuando algo del radar le llame la atención, la primera pregunta que se haga sea "¿por
qué está barata?" en vez de "¿cuánto va a subir?".

Si termina abriéndola solo para mirar el precio, se convirtió en Fintual con más pasos.
