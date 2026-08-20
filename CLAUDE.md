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
`watchlist.txt`), `web/api/tesis.ts` (edita `data/tesis.json`) — ambas escriben en este
mismo repo con `GITHUB_WRITE_TOKEN` — y `web/api/mi-inversion.ts`, que en cambio escribe en
un repo aparte y privado, `inversiones-privado`, con un token distinto
(`GITHUB_WRITE_TOKEN_PRIVADO`). Ver la excepción explícita más abajo para el porqué de ese
repo separado.

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
`web/api/watchlist.ts` y `web/api/tesis.ts`), `GITHUB_WRITE_TOKEN_PRIVADO` (fine-grained
PAT distinto, permiso Contents R/W acotado *solo* al repo `inversiones-privado`, usado por
`web/api/mi-inversion.ts` — separado del token de arriba a propósito, para no ampliarle el
alcance a un token que ya escribe en el repo público), `WATCHLIST_EDIT_KEY` (clave
compartida que protege el POST de esos tres endpoints — no es autenticación real, es el
candado mínimo para una app de un solo usuario).

## Pendiente (al cerrar la sesión del 2026-08-19)

Todo lo de abajo ya está commiteado y deployado a producción — lo que falta es que José lo
pruebe desde su celular y decida los próximos pasos. No asumir que algo de esto está
aprobado para seguir sin que él confirme primero.

- **Testeo pendiente del usuario** (nada bloqueante, solo falta que lo use): comprar/
  vender/editar/borrar en "mi inversión" (`MiInversion.tsx`) con clave real — el flujo
  completo solo se probó con clave incorrecta (401) porque no tengo el `WATCHLIST_EDIT_KEY`
  real; los recuadros "HOY"/"TU POSICIÓN" del header; el contraste del tooltip del gráfico;
  el contexto nuevo en métricas avanzadas y Radar; los resúmenes de Mundo/Chile más largos
  (esto último ya confirmado corriendo en `daily.json`, solo falta que él lo lea y opine).

- **Contexto de métricas — iteración 2 (pendiente de decisión):** se implementó la
  iteración 1 (rangos de referencia fijos tipo libro de texto, `web/src/lib/
  referenciasMetricas.ts`). José pidió probar esa primero y evaluar después si vale la pena
  una iteración 2 con explicación más larga generada por Gemini. No armar la iteración 2
  hasta que él la pida explícitamente después de probar la 1.

- **Semáforo de recomendación de compra (verde→rojo):** José lo propuso, se le explicó que
  choca con la regla dura "el Radar nunca genera texto tipo 'deberías comprar'" y por qué
  existe esa regla. Se ofreció como alternativa compatible el contexto de métricas de arriba,
  y José lo aceptó en su lugar — pero nunca dijo explícitamente "no lo construyas nunca". Si
  lo vuelve a pedir después de probar el contexto de métricas, aplica el protocolo de
  siempre: señalar el choque con la regla, preguntar si de verdad quiere la excepción, y si
  dice que sí, documentarla acá con fecha antes de construirla.

- **Buscador de data avanzada para cualquier ticker** (sin necesidad de agregarlo a la
  watchlist): idea de José, no empezada. Requeriría una función serverless que llame EDGAR/
  Finnhub en vivo al buscar (Vercel no corre Python, así que habría que reimplementar en
  TypeScript partes de lo que hoy hace el collector) — choca con la frase "el visor sigue sin
  llamar APIs en vivo para mostrar datos" de la sección Stack. Factible en $0, pero es un
  proyecto en sí mismo, no un ajuste rápido. Conversarlo con calma antes de empezar a picar
  código, no asumir alcance.

- **Extender "métricas avanzadas" completas al Radar** (Market Cap, EV, ROE, P/E, etc. —
  hoy el Radar solo tiene los 3 campos de screening: `ingresos_var_pct`, `margen_op`,
  `deuda_patrimonio`): se lo propuse a José como respuesta a "necesito más data para
  decidir", pero la conversación se desvió hacia el contexto de métricas y nunca confirmó si
  quiere esto también. Preguntar antes de construirlo — no es trabajo ya aprobado.
