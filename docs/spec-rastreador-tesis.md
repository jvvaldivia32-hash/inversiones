# Spec: Rastreador de Tesis de Inversión

**Para:** Claude Code (WSL)
**Stack:** Python / Streamlit / Google Sheets / Gemini 2.5 Flash
**Deploy:** Streamlit Cloud

---

## 1. Qué es esto (y qué NO es)

**NO es** un dashboard de precios. Fintual ya muestra precios. Duplicarlo no agrega nada y
además invita a mirar la pantalla todos los días, que es exactamente el comportamiento que
queremos evitar.

**SÍ es** un rastreador de tesis falsables. El usuario escribe una tesis con umbrales
numéricos concretos ANTES de invertir. Cuando la empresa reporta resultados (4 veces al año),
el sistema trae los números reales, los compara contra los umbrales y devuelve un semáforo.

El valor está en obligar a escribir la tesis antes, y en no dejar que se reescriba después
de conocer el resultado.

---

## 2. Restricción de datos (leer antes de diseñar)

Los datos vienen de dos lugares distintos y NO son intercambiables:

### 2.1 SEC EDGAR API — datos estructurados

- Base: `https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json`
- Gratis, sin API key.
- **Requiere header `User-Agent` con nombre y email real.** Sin eso, SEC bloquea (403).
- Rate limit: 10 req/seg. Respetarlo o te banean la IP.
- Índice de filings: `https://data.sec.gov/submissions/CIK{cik}.json`

Tags XBRL útiles:

| Dato | Tag `us-gaap` |
|---|---|
| Ingresos | `RevenueFromContractWithCustomerExcludingAssessedTax` |
| Operating income | `OperatingIncomeLoss` |
| Net income | `NetIncomeLoss` |
| EPS diluido | `EarningsPerShareDiluted` |
| Capex | `PaymentsToAcquirePropertyPlantAndEquipment` |
| Flujo operativo | `NetCashProvidedByUsedInOperatingActivities` |

CIK de referencia: MSFT `0000789019`, MCD `0000063908`, BRK.B `0001067983`.

### 2.2 Press release (8-K Exhibit 99.1) — datos en prosa

Métricas como "Azure and other cloud services revenue increased 43%" **no existen en XBRL**.
Microsoft nunca publica los dólares de Azure, solo el porcentaje, y solo en texto.

Lo mismo aplica a:
- Guidance del próximo trimestre
- Comparable sales de MCD
- Cualquier métrica de segmento no auditada

Flujo: buscar el 8-K más reciente en el índice de submissions → bajar el Exhibit 99.1 →
pasarlo a Gemini para extracción estructurada.

---

## 3. Modelo de datos (Google Sheets)

### Hoja `tesis`

| Columna | Tipo | Ejemplo |
|---|---|---|
| `id` | str | `msft-azure-2026q4` |
| `ticker` | str | `MSFT` |
| `cik` | str | `0000789019` |
| `tesis` | str | "El lock-in enterprise sostiene el crecimiento de Azure" |
| `metrica` | str | `azure_growth_pct` |
| `umbral_verde` | float | `40` |
| `umbral_rojo` | float | `30` |
| `direccion` | str | `mayor_es_mejor` \| `menor_es_mejor` |
| `fecha_escrita` | date | `2026-08-10` |
| `estado` | str | `activa` \| `cumplida` \| `rota` |
| `notas_cierre` | str | (se llena al cerrar) |

**Regla dura:** `tesis`, `metrica` y los umbrales son inmutables una vez escritos. Si el
usuario quiere cambiarlos, se crea una tesis NUEVA y la vieja se cierra con motivo. Sin esto
el sistema no sirve para nada — se convierte en una máquina de racionalizar a posteriori.

### Hoja `lecturas`

| Columna | Ejemplo |
|---|---|
| `tesis_id` | `msft-azure-2026q4` |
| `periodo` | `FY26Q4` |
| `fecha_reporte` | `2026-07-29` |
| `valor` | `43.0` |
| `semaforo` | `verde` |
| `fuente_url` | (link al 8-K) |
| `cita_textual` | "Azure and other cloud services revenue increased 43%" |
| `extraido_por` | `gemini` \| `xbrl` |

`cita_textual` es obligatorio cuando `extraido_por = gemini`. Si Gemini no puede citar la
frase exacta del documento, la lectura se marca `requiere_revision` y no se guarda como dato.

---

## 4. Lógica del semáforo

```
si direccion == mayor_es_mejor:
    valor >= umbral_verde  -> VERDE   (tesis intacta)
    umbral_rojo <= valor   -> AMARILLO (desaceleración, revisar si el precio ya lo asume)
    valor <  umbral_rojo   -> ROJO    (tesis rota)
```

Invertir comparaciones si `direccion == menor_es_mejor`.

El semáforo **no recomienda comprar ni vender**. Solo dice si lo que el usuario predijo
está pasando o no. La decisión es del usuario.

---

## 5. Extracción con Gemini

Prompt estructurado, salida JSON estricta:

```
Eres un extractor de datos financieros. Del documento adjunto, extrae UNICAMENTE
la métrica solicitada.

Métrica: {descripcion_metrica}

Responde SOLO con JSON, sin markdown ni preámbulo:
{
  "valor": <número o null>,
  "unidad": "porcentaje" | "millones_usd" | null,
  "cita": "<la frase EXACTA del documento donde aparece>",
  "encontrado": true | false
}

Si no encuentras la métrica, devuelve encontrado=false y valor=null.
NUNCA infieras, calcules ni estimes el valor. Solo extrae lo que está escrito literal.
```

**Validación obligatoria post-respuesta:** verificar que `cita` aparezca como substring
literal del documento original. Si no aparece, descartar la extracción y marcar
`requiere_revision`. Esto mata la alucinación de raíz.

Reusar `get_secret()` del CRM para la key. Rate limiting: Bug #8 del CRM aplica igual acá,
aunque el volumen es mucho menor (4 llamadas por ticker al año).

---

## 6. Trigger

Earnings son trimestrales. No tiene sentido correr esto a diario.

**v1:** botón "Revisar ahora" en la UI. El usuario aprieta cuando se entera que reportaron.

**v2:** chequeo automático contra el índice de submissions de EDGAR — si aparece un 8-K
nuevo con Exhibit 99.1 desde la última revisión, correr la extracción. Guardar el
`accessionNumber` del último procesado para no repetir.

No construir v2 hasta que v1 funcione con al menos un ciclo real de earnings.

---

## 7. UI (Streamlit, 3 vistas)

### Vista 1 — Tesis activas
Una card por tesis: texto de la tesis, métrica, semáforo actual, última lectura, fecha del
próximo reporte esperado.

### Vista 2 — Escribir tesis nueva
Formulario que **obliga** a completar los cuatro campos: tesis en prosa, métrica, umbral
verde, umbral rojo. No se puede guardar incompleta.

Validación anti-vaguedad: rechazar tesis que no contengan un sustantivo del negocio. Si el
texto es "va a subir" o "está barata", no pasa. Debe referirse a algo que ocurre en la
empresa, no en el precio.

### Vista 3 — Historial
Lecturas anteriores por tesis, con link a la fuente y la cita textual. Sirve para ver la
trayectoria de la métrica trimestre a trimestre — que es donde se ve la aceleración o
desaceleración real.

---

## 8. Orden de construcción

1. Cliente EDGAR con `User-Agent` correcto + rate limiting. Probar contra CIK de MSFT y
   verificar que devuelve el FY26Q4.
2. Persistencia en Sheets (reusar el patrón del CRM).
3. Semáforo + UI de tesis activas, con datos XBRL solamente.
4. Extractor Gemini + validación de cita literal.
5. Historial.
6. (Después) Trigger automático.

Cada paso debe funcionar solo antes de pasar al siguiente. El paso 1 es el que más se
subestima: si el `User-Agent` está mal, todo lo demás falla en cascada y cuesta diagnosticar.

---

## 9. Fuera de alcance (v1)

- Precios en tiempo real
- Cualquier recomendación de compra/venta
- Cálculo de valor intrínseco / DCF
- Alertas por precio
- Más de 5 tickers

---

## 10. Métrica de éxito

Que el usuario pueda responder, para cada peso invertido: *"metí plata porque creo que X va
a pasar, y si Y no ocurre estaba equivocado"* — con X e Y escritos antes de invertir y
verificables contra un documento oficial.

Si la app funciona técnicamente pero el usuario sigue decidiendo por "subió mucho", falló.
