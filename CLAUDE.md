# Dashboard de Inversiones — Reglas del Proyecto

Lee `docs/plan-app-inversiones.md` completo antes de escribir código. Es la fuente de verdad
de arquitectura, fases y modelo de datos. `docs/spec-rastreador-tesis.md` se integra recién
en la Fase 7 — no lo toques antes de eso.

## Regla de fases

No avanzar a la siguiente fase hasta que la actual cumpla su criterio "Termina cuando" del
plan. Si no está claro que se cumplió, preguntar antes de seguir. No adelantar trabajo de
una fase futura "ya que estamos".

## Reglas duras (no negociables, no las relajes aunque parezca más simple sin ellas)

**EDGAR:** todo request a `data.sec.gov` lleva header `User-Agent` con nombre y correo real
(viene en la variable de entorno `SEC_USER_AGENT`). Sin esto: 403. Probar el cliente aislado
contra el CIK de MSFT (`0000789019`) antes de integrarlo a cualquier otra cosa.

**Extracción con Gemini:** toda cifra que Gemini extraiga de un press release debe venir con
una cita textual. Validar en código que esa cita exista como substring literal del
documento original. Si no existe, descartar la extracción — nunca guardar el valor igual.

**Copyright:** las noticias se agregan, no se republican. Máximo 1-2 frases de extracto por
artículo, siempre reescritas por Gemini, nunca copiadas del original. Link a la fuente
siempre visible.

**Costo: $0/mes, sin excepciones.** Todo corre en free tier (GitHub Actions, Vercel Hobby,
EDGAR, Finnhub free, Gemini free tier, Banco Central). Si algo requiere plan pago, parar y
avisar antes de implementarlo — no asumir que está bien.

**Diseño — el color es solo señal.** Verde/ámbar/rojo/acento únicamente para estado
(semáforo de tesis, radar aprobado/descartado, links). Todo lo demás en la escala de grises
de `tokens.css`. No agregar color decorativo aunque "se vea más lindo".

> **Excepción explícita (decidida por el usuario, 2026-08-11):** el gráfico de precio
> (`GraficoPrecio.tsx`) sí puede llevar un relleno degradado bajo la línea, usando
> `--acento` desvaneciendo a transparente — no un color nuevo.
>
> **Excepción explícita #2 (decidida por el usuario, 2026-08-13):** la línea de
> comparación del mismo gráfico (`comparar con...`) usa `--rojo` en vez de gris para
> distinguirse de la línea principal. Ojo: `--rojo` significa "negativo/roto" en todo
> el resto de la app (variación diaria a la baja, tesis rota, descartado en el radar) —
> acá no tiene ese significado, es solo la segunda serie del gráfico. Riesgo conocido y
> aceptado, no un descuido.
>
> Estas dos son las únicas excepciones decorativas a esta regla. No las uses como
> precedente para agregar color en otro lado sin preguntar primero.

**Radar:** solo muestra candidatos con sus datos. Nunca genera texto tipo "deberías
comprar". Los descartados se muestran siempre, con el motivo — no se ocultan.

**Tesis (Fase 7+):** inmutable una vez escrita. Editar = cerrar la vieja y crear una nueva.
Nunca sobreescribir los umbrales de una tesis existente.

## Stack

Recolector: Python, corre en GitHub Actions por cron. Visor: React + Vite, deploy en
Vercel. Un repo, dos carpetas (`collector/`, `web/`). El visor sigue sin llamar APIs en vivo
para *mostrar* datos de mercado — precios, noticias, fundamentales vienen únicamente de
`data/daily.json`. La excepción son caminos acotados de lectura/escritura de datos propios
del usuario, cada uno una función serverless de Vercel que habla directo con la API de
GitHub (nunca con un token en el navegador): `web/api/watchlist.ts` (edita
`watchlist.txt`), `web/api/tesis.ts` (edita `data/tesis.json`) y `web/api/paperinvesting.ts`
(edita `data/paperinvesting.json`, simulador de cartera ficticia — ver Pendiente) — las tres
escriben en este mismo repo con `GITHUB_WRITE_TOKEN` — y `web/api/mi-inversion.ts`, que en
cambio escribe en un repo aparte y privado, `inversiones-privado`, con un token distinto
(`GITHUB_WRITE_TOKEN_PRIVADO`). Ver la excepción explícita más abajo para el porqué de ese
repo separado (y por qué `paperinvesting.ts` NO sigue ese mismo patrón: es plata ficticia,
no hay nada que proteger).

> **Excepción explícita #3 (decidida por el usuario, 2026-08-18):** "mi inversión"
> (monto actual en USD y % de ganancia por posición, cargados a mano por el usuario) se
> guarda en un repo de GitHub aparte y privado (`inversiones-privado`), no en este repo
> público, y no solo en `localStorage` del navegador. La primera versión de esta feature
> guardaba todo en `localStorage` (sin sincronizar entre dispositivos); el usuario pidió
> sincronización real y aceptó bajar la privacidad a "repo privado" en vez de "solo este
> navegador" — pero **no** haciendo privado este repo principal: se midió el uso real de
> minutos de GitHub Actions (los 4 workflows de cron, ~1.500 de los 2.000 min/mes gratis
> que da un repo privado, ~75% ya usado solo con el cron actual) y hacer privado este repo
> hubiera arriesgado la regla dura de "$0/mes, sin excepciones" apenas creciera el
> collector. Repo público sin tope de minutos + repo aparte solo para este dato = privacidad
> real sin ese riesgo. No usar este caso como precedente para mover más datos fuera de este
> repo sin medir de nuevo el costo real.

## Secrets

Nunca hardcodear keys en el código. Todo vía variables de entorno / GitHub Secrets:
`GEMINI_API_KEY`, `FINNHUB_KEY`, `SEC_USER_AGENT`, `BCCH_API_KEY` (token único de la API BDE
del Banco Central — el portal se rediseñó en algún momento de 2024+ y pasó de usuario/
contraseña por query params a un token único; el servicio SOAP viejo todavía pide
usuario/contraseña pero no se usa acá, se usa el REST con `?token=`),
`GITHUB_WRITE_TOKEN` (fine-grained PAT, solo permiso Contents R/W sobre este repo, usado por
`web/api/watchlist.ts`, `web/api/tesis.ts` y `web/api/paperinvesting.ts`),
`GITHUB_WRITE_TOKEN_PRIVADO` (fine-grained PAT distinto, permiso Contents R/W acotado *solo*
al repo `inversiones-privado`, usado por `web/api/mi-inversion.ts` — separado del token de
arriba a propósito, para no ampliarle el alcance a un token que ya escribe en el repo
público), `WATCHLIST_EDIT_KEY` (clave compartida que protege el POST de esos cuatro
endpoints — no es autenticación real, es el candado mínimo para una app de un solo usuario).

## Pendiente (al cerrar la sesión del 2026-08-24, ya de madrugada del 25)

Todo lo de abajo ya está commiteado — lo que falta es deployar (si no corrió solo) y que
José lo pruebe desde su celular y decida los próximos pasos. No asumir que algo de esto está
aprobado para seguir sin que él confirme primero.

- **Lo primero al retomar (2026-08-25):** José todavía no vio nada de lo del 24 en el
  celular. Antes de picar código nuevo, preguntarle qué le pareció: el rango "10A" del
  gráfico (¿se lee bien el eje rotulando año por medio?), los puntos de color por métrica
  (¿los umbrales le hacen sentido, sobre todo qué quedó ámbar vs. rojo?) y las dos cards por
  fila del simulador. Todo eso está pusheado y desplegado.

- **Testeo pendiente del usuario** (nada bloqueante, solo falta que lo use): comprar/
  vender/editar/borrar en "mi inversión" (`MiInversion.tsx`) con clave real — el flujo
  completo solo se probó con clave incorrecta (401) porque no tengo el `WATCHLIST_EDIT_KEY`
  real; los recuadros "HOY"/"TU POSICIÓN" del header; el contraste del tooltip del gráfico;
  los resúmenes de Mundo/Chile más largos (esto último ya confirmado corriendo en
  `daily.json`, solo falta que él lo lea y opine).

- **Contexto de métricas — ahora también en tus posiciones, no solo en Radar** (2026-08-20):
  José notó que PEP (una card del Radar) mostraba "Ingresos: crecimiento saludable" etc. pero
  sus posiciones reales no — el contexto (`referenciasMetricas.ts`) solo se había cableado en
  `Radar.tsx`. Se agregó el mismo bloque de 3 líneas a `CardInversion.tsx` (visible apenas se
  abre la card, no hace falta entrar a "métricas avanzadas"), más una fila nueva "Deuda /
  patrimonio" dentro de "métricas avanzadas" (`metricas_avanzadas.deuda_patrimonio`, mismo
  cálculo y misma excepción para bancos que ya usaba el Radar). **Confirmado 2026-08-24:**
  `deuda_patrimonio` ya viene con dato real en `daily.json`, así que esto quedó cerrado.

- **Contexto de métricas — iteración 2 con Gemini (pendiente de decisión):** sigue sin
  empezar, sin cambios respecto a la sesión anterior. No armar hasta que José la pida
  explícitamente después de probar lo de arriba.

- **Simulador de cartera ficticia / "paper investing"** (2026-08-20, extra fuera del plan
  madre, pestaña nueva "Simulador"): parte con US$5.000 ficticios
  (`data/paperinvesting.json`, sembrado a mano) + un cron mensual nuevo
  (`.github/workflows/paper_aporte_mensual.yml`, día 1 de cada mes) que suma US$100. Compra/
  venta reusa `MiInversion.tsx` generalizado (`endpoint`/`permitirEditar` como props nuevas)
  contra `web/api/paperinvesting.ts` (repo público, `GITHUB_WRITE_TOKEN` — a diferencia de
  "mi inversión" real, acá no hay plata real que proteger). Universo comprable: watchlist +
  candidatos del Radar (~18 tickers, los únicos con precio+`serie_precio` completos hoy en
  `daily.json`) — José hizo notar que no hacía falta pedirle nada nuevo a Finnhub para esto,
  se puede reusar tal cual. Si compras algo que luego deja de ser candidato del Radar (la
  lista cambia semana a semana), la card se queda sin gráfico/precio fresco hasta que vuelva
  a aparecer — limitación conocida de v1, no un bug. Sin gráfico de "valor total de la
  cartera en el tiempo" todavía (necesitaría snapshots diarios, es v2 si lo pide). Sin acción
  "editar" (acá no hay bróker externo con el que reconciliar). **Pendiente: que José lo
  pruebe** (comprar algo de la watchlist y algo del Radar, vender una fracción) y que corra
  la primera vez el cron mensual o que se confirme que el archivo semilla alcanza mientras
  tanto.

- **Histórico de precio a 10 años (hecho y commiteado 2026-08-24):** el gráfico tiene rango
  "10A" además de "5A". `compactar()` en `collector/historico.py` pasó a tres tramos
  (horario 45d / diario 2a / semanal 10a) en vez de dos: el gráfico ya dibujaba 5A con un
  punto por semana, así que guardar 250 puntos por año para dibujar 52 era peso puro — con
  la escalera nueva el archivo queda en ~1.270 puntos por ticker, casi lo mismo que ocupaban
  5 años diarios, con el doble de historia. `collector/backfill_10a.py` es el script de una
  sola vez que le vuelve a pedir los 10 años a Yahoo (no está en ningún workflow a
  propósito): ya se corrió sobre los 83 tickers y respondieron los 83. Ante choque de
  timestamp **gana lo ya guardado**, para no pisar la resolución horaria propia del cron con
  el cierre ajustado de Yahoo; se verificó que ningún ticker perdió puntos de los últimos 45
  días. EA, LTM y RBLX no llegan a 10 años porque cotizan desde después de 2016 — no es un
  bug. Pendiente: que corra el próximo cron para que `serie_precio` en `daily.json` traiga la
  clave `10A` (hasta entonces el botón "10A" del gráfico no dibuja nada), y que José lo mire.

- **Señal verde/ámbar/rojo por métrica (hecho y commiteado 2026-08-24):** la versión acotada
  del semáforo que José pidió — "no explícitamente COMPRA, sino buen X / mal X en datos
  específicos". Cada lectura de `referenciasMetricas.ts` devuelve ahora `{texto, nivel}` y
  `SenalMetrica.tsx` la pinta como punto de color en Radar, `CardInversion` y
  `MetricasAvanzadas`. **Es por métrica y nada más:** no se suman los niveles ni se deriva de
  ellos un veredicto agregado tipo "7 de 10" — eso choca con la regla dura del Radar y es
  otra decisión, hay que preguntarle antes. `neutro` no pinta color (el color es solo señal, y
  "está en el rango normal" es la ausencia de una). Ámbar vs. rojo: valoración cara, deuda
  alta o volatilidad son ámbar (elecciones de perfil, no defectos del negocio); rojo solo para
  "pierde plata o se está encogiendo". De paso se arregló un bug de `banda()`: cuando ningún
  tramo cubría el valor devolvía el tramo más bajo, así que MCD con deuda/patrimonio −38,97
  salía como "deuda baja". Pendiente: que José lo vea desplegado y diga si los umbrales le
  hacen sentido.

- **Atajo "Actualidad" del nav, solo en mobile (hecho y commiteado 2026-08-24):** desde
  960px Actualidad ya es la columna izquierda sticky de la vista "Hoy", así que el botón del
  nav no llevaba a ningún lado que no se viera ya. En mobile sigue.

- **Simulador: dos cards por fila (hecho y commiteado 2026-08-24):** el simulador ya vivía
  dentro del breakout ancho (`.vista-ancha`, 1200px) pero apilaba las posiciones en una sola
  columna, así que cada card se estiraba a todo el ancho y el gráfico quedaba demasiado
  gordo. Ahora usa el mismo breakpoint y la misma medida que `.posiciones-lista` de
  "Inversión" (`minmax(380px, 1fr)`, que a 1200px da dos columnas y no tres) para que las
  dos vistas se vean igual. Si alguna vez se toca una de las dos medidas, tocar la otra.

- **Semáforo de recomendación de compra (verde→rojo):** parcialmente resuelto por la señal
  por métrica de arriba, que es hasta dónde llega sin chocar con la regla dura del Radar. Lo
  que sigue prohibido sin preguntarle primero es el paso siguiente: sumar esas señales en un
  puntaje o veredicto único por ticker. Mismo protocolo si lo vuelve a pedir: señalar el
  choque, preguntar, documentar acá si dice que sí.

- **Buscador de data avanzada para cualquier ticker:** sin cambios, sigue sin empezar.
  Conversarlo con calma antes de picar código.

- **Extender "métricas avanzadas" completas al Radar:** sin cambios, sigue sin confirmar.
