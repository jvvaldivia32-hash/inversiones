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

Recolector: Python, corre en GitHub Actions por cron (seis workflows: el horario
`daily.yml`, más Radar semanal, Fintual diario, Amigos diario, el aporte mensual del
simulador y el resumen matutino de Telegram). Visor: React + Vite, deploy en Vercel.
Un repo, dos carpetas (`collector/`, `web/`). El visor sigue sin llamar APIs en vivo
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
endpoints — no es autenticación real, es el candado mínimo para una app de un solo usuario),
`TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` (el bot que manda las alertas de movimiento fuerte
y el resumen de la mañana; si falta cualquiera de los dos, todo el camino de Telegram es un
no-op silencioso y el recolector sigue igual — nunca tumba una corrida por un aviso).

Aparte de los secrets hay una *variable* (no secret) opcional, `APP_URL`, que solo agrega el
link "Ver todo en la app" al pie del resumen matutino. Va en Settings → Secrets and variables
→ Actions → pestaña **Variables**, no en Secrets: es una URL pública, no hay nada que ocultar.

## Pendiente (al 2026-08-30)

**Contexto de arranque:** hay **un frente abierto nuevo y con datos**: el throttling de los
cron de GitHub volvió, y el arreglo del 27-08 (`:17`/`:47`) resultó insuficiente. Se había
dado por resuelto el 28-08 mirando un solo día — ver punto 2, que vuelve a estar ABIERTO.
Eso arrastra dos consecuencias que José todavía no comentó: el resumen "de la mañana" le
está llegando **cerca del mediodía**, y la app pasa tramos de 5-6 horas sin actualizarse.

Lo demás de infraestructura está bien: la sesión del 28-08 cerró una pasada de debug con
cinco bugs arreglados y pusheados (punto 7), todos verificados en un run real.

Lo que sigue sin mirarse es todo lo de los puntos 5 y 6 — José no ha visto nada de lo del
24 de agosto. No asumir que algo está aprobado para seguir sin que él lo mire y confirme
primero.

### 1. Telegram — andando, pero el resumen llega tarde (2026-08-30)

José creó el bot con @BotFather y cargó `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en Actions
→ Secrets. Un run manual del resumen le llegó al celular y lo confirmó pegando el mensaje;
los precios del aviso coincidían exacto con `daily.json`.

Ese mismo día pidió que el resumen fuera **todos los días** en vez de lun-vie (commit
`fa36b9f`, `38 11 * * *`): lo quiere como rutina fija de la mañana. Que sábado y domingo
repitan el cierre del viernes es lo buscado, no un defecto — si lo reporta como "se quedó
pegado", esa es la explicación.

`11:38 UTC` = 07:38 Chile en invierno y 08:38 en verano (verificado con zoneinfo; el
comentario del workflow decía lo contrario y se corrigió en `66516dc`). GitHub no entiende
husos horarios, el cron es siempre UTC, así que la hora local se corre sola cuando Chile
cambia de horario. En los dos casos queda antes de que abra el mercado.

**El resumen automático sí sale, pero no de mañana (medido el 30-08).** Los dos runs
terminaron `success` y con "Resumen enviado" en el log, así que a José le llegó — pero el
cron de las **11:38 UTC disparó a las 15:44 UTC el 29-08 y a las 15:26 UTC el 30-08**: casi
cuatro horas tarde, o sea cerca de las 11:30 de Chile y **después de que abre el mercado**
(13:30 UTC). Es el mismo throttling del punto 2, no un error del script.

Rompe la premisa de la feature ("antes de que abra el mercado"). Tres caminos, ninguno
elegido todavía — **preguntarle a José antes de tocar nada**:

1. **Colgar el resumen del recolector** en vez de un cron propio: el primer run del día
   pasada cierta hora manda el mensaje, con un archivo de estado como el de las alertas
   (`data/alertas_enviadas.json`). No agrega terceros y se apoya en los ~12 disparos que
   sí llegan al día, pero la hora exacta sigue sin ser garantía.
2. **Adelantar el cron** (p. ej. 09:00 UTC) para que aun llegando cuatro horas tarde caiga
   antes de la apertura. Barato, pero es apostarle a que el retraso no crezca.
3. **Disparador externo**, mismo remedio que el punto 2 y las mismas objeciones.

**Las alertas de ±5% siguen sin verse en la práctica** — solo saltan cuando algo se mueve de
verdad, y entre el 28 y el 30 no pasó (el log dice `sin movimientos de ±5.0% entre 20
tickers vigilados`). Cuando le llegue la primera, preguntarle si el umbral le sirve o si es
mucho ruido: es una constante sola, `UMBRAL_PCT` en `collector/alertas.py`.

**Sin cargar (opcional, no es un error):** `APP_URL` en la pestaña **Variables** (no
Secrets). Sin ella el resumen sale sin el link "Ver todo en la app". La URL de Vercel no
está en el repo — hay que preguntársela.

### 1b. El precio no es en vivo — preguntado y respondido (2026-08-28)

José notó que la app difiere "un par de dólares" de Yahoo Finance y preguntó si era un bug o
un problema de tickers. **No es ninguna de las dos** y no hay que salir a buscar un bug si lo
vuelve a mencionar:

- Comparado con Yahoo con 8 minutos de diferencia, los cuatro tickers coincidían dentro de 33
  centavos (MSFT, 1 centavo).
- `BRK.B` (Finnhub) vs `BRK-B` (Yahoo) es la misma acción y da el mismo número. El mapeo está
  bien.
- La causa es que el recolector corre una vez por hora y el visor nunca llama APIs en vivo.
  Ese mismo día MSFT tuvo recorridos de **$6,71 dentro de una sola hora** de sesión.

Precio en vivo obligaría al navegador a pegarle a una API de mercado: plan pago, choca con la
regla de $0/mes y con "el visor no llama APIs en vivo". **Ofrecido y no pedido:** el header
ya muestra `Actualizado hoy HH:MM` (`web/src/App.tsx`) pero en hora absoluta; pasarlo a
relativo ("hace 23 min") haría obvia la antigüedad del dato. No tocarlo sin que lo pida.

### 2. GitHub vuelve a botar los cron — REABIERTO (2026-08-30)

Esto es lo que motivó la sesión del 27: la app llevaba horas sin actualizarse.

**Diagnóstico (con datos, no con corazonada):** GitHub estaba botando los eventos `schedule`
de este repo. Hasta el 26-08 14:00 UTC el recolector corría casi cada hora; después se
degradó y el 27 se cortó del todo — 14+ horas sin un solo run programado, incluidos los
daily de Fintual y Amigos. Descartado uno por uno: no era el collector (todos los runs que
sí corrieron terminaron `success`), no era cuota (repo público, minutos ilimitados), no eran
los workflows (los cinco `active`), no era un incidente (githubstatus.com operacional). Y
los runs que sí llegaban arrancaban a minutos random (:12, :28, :37) en vez de :00 — la
firma clásica de la cola de Actions.

**El arreglo (commit `2b3a851`) funcionó.** Ningún workflow arranca ya en :00 ni :30, los
dos minutos más congestionados de GitHub; `daily.yml` quedó con `:17` principal y `:47` de
respaldo, y el respaldo sale en ~10 segundos si `data/daily.json` tiene menos de 45 minutos
(paso `frescura`). No son dos recolecciones: el tramo horario de `historico_precios.json`
guarda todos los puntos que le llegan, así que recolectar dos veces por hora duplicaría ese
archivo (5,1 MB) a cambio de nada. El 28-08 los eventos `schedule` volvieron (runs a las
05:49 y 06:09 UTC) y se dio por resuelto — **conclusión apurada, sacada de un solo día.**

**Pero el mismo commit traía un bug que mataba todos esos runs** (arreglado en `7c3a833`):
el paso `frescura` manda su stdout completo a `$GITHUB_OUTPUT`, y ahí se colaba la línea de
debug `# daily.json generado hace N min`. Actions rechaza cualquier línea que no sea
`clave=valor` y tumbaba el run entero con `Invalid format` — después de haber decidido bien
`correr=si`. Esa línea ahora va a stderr: se sigue viendo en el log pero no toca el output.
Lección para la próxima: un cambio de workflow no está listo hasta verlo correr de verdad,
`workflow_dispatch` sirve justo para eso y no sufre el throttling.

De paso (el 27) se endureció el push de `daily.yml`: antes hacía `git pull --rebase` a secas
y si dos runs se pisaban, el segundo moría con un conflicto en `daily.json`. Ahora el
snapshot recién generado gana: se rearma sobre `origin/main` y reintenta hasta 3 veces.

**Recaída, medida el 30-08.** Los eventos vuelven a llegar a cuentagotas, y el minuto
`:17`/`:47` no alcanzó: llegan tarde en vez de no llegar.

- Runs `schedule` de `daily.yml` por día (de 48 posibles: 24 principales + 24 respaldos):
  25-08: 14 · 26-08: 17 · 27-08: 2 · 28-08: 4 · 29-08: 11 · **30-08: 12**.
- Los que llegan, llegan corridos: el disparo de `:17` cae a `:24`, `:34`, `:39`, `:58`.
  Sigue siendo la firma de la cola de Actions, no un problema del repo — todos terminan
  `success`, repo público sin tope de minutos.
- El efecto real está en los commits del bot: el 30-08 hubo **8 recolecciones**, con huecos
  de 01:40→06:47 (5 h) y 06:47→12:59 (6 h). O sea que la app muestra un precio de hace
  horas buena parte del día.

**El disparador externo vuelve a estar sobre la mesa** (cron-job.org pegándole a
`workflow_dispatch`, que no sufre el throttling — se comprobó el 28-08: el run manual salió
al instante). Cuesta meter una pieza de terceros y un PAT fuera del repo, así que **no
implementarlo sin que José lo decida**. La otra mitad del problema (el resumen matutino) se
puede arreglar sin terceros — ver punto 1.

### 3. Telegram: alertas de movimiento fuerte + resumen de la mañana (hecho, commit `8aad509`)

Lo pidió José a mitad de sesión. Los parámetros los eligió él el 2026-08-27: **las dos
cosas**, umbral **±5%**, sobre **watchlist + candidatos del Radar** (descartó explícitamente
el simulador y sus posiciones reales — o sea *no* hubo que darle al repo público un token de
lectura sobre `inversiones-privado`, la excepción #3 sigue intacta).

- **Alertas** (`collector/alertas.py`, enganchado al final de `collector/main.py`): corre
  pegado al recolector horario, así que el aviso sale en el mismo run que detecta el
  movimiento — no hay un segundo cron esperando. Antiduplicado en
  `data/alertas_enviadas.json`: un ticker no repite el mismo día *salvo* que se mueva otro 5%
  entero (5% → 10% → 15%), y el día se cuenta según Nueva York, no según UTC, para que un run
  de las 00:30 UTC no reinicie la sesión de ayer y reavise todo. Si el envío falla no se
  guarda el estado, así el próximo run reintenta en vez de dar por avisado algo que nunca
  llegó.
- **Resumen matutino** (`collector/resumen_telegram.py` + `.github/workflows/
  resumen_telegram.yml`, 11:38 UTC lun-vie ≈ 07:38 Chile, antes de que abra el mercado): tus
  tickers ordenados por cuánto se movieron, índices, referencias de Chile y dos titulares de
  cada bloque. Sale entero de `daily.json`, sin `pip install` ni una sola llamada a APIs.
  Renderizado contra la data real: 1.434 caracteres, cómodo bajo el tope de 4.096 de Telegram.
- **Ninguno de los dos aconseja nada** — precio, variación y el titular con link, igual que el
  Radar. Los extractos son los que Gemini ya reescribió, nunca texto copiado (reglas duras de
  Radar y de copyright).
- La watchlist ya trae `var_dia_pct` en `daily.json`; los candidatos del Radar **no** (su
  `serie_precio` solo se refresca en el cron semanal), así que se les pide la quote a Finnhub:
  ~16 llamadas por hora, muy dentro del free tier de 60 por minuto, y **no** se guardan en el
  histórico para no engordarlo con tickers que el Radar puede sacar la semana que viene.
- 29 tests nuevos (`test_alertas.py`, `test_resumen_telegram.py`); la suite entera queda en
  183 pasando. Los 3 módulos que no corren localmente (`test_amigos`, `test_noticias`,
  `test_rss`) es solo que falta `feedparser` en esta máquina — nada que ver con esto.

**Pendiente:** que José ponga los secrets (punto 1) y después diga si el umbral de 5% le
suena bien en la práctica y si el resumen de las 07:38 trae lo que quiere ver. El umbral es
una constante sola, `UMBRAL_PCT` en `collector/alertas.py`.

### 4. Bug de las tesis que no se guardaban — RESUELTO (2026-08-28, commit `5302b8e`)

`collector/main.py` llamaba a `_guardar_tesis()` en cada corrida, pero `daily.yml` nunca
commiteaba `data/tesis.json`: cada revisión automática de tesis (`_revisar_tesis_ticker`, el
semáforo pasando a ámbar o a roto) se escribía en el runner y se tiraba a la basura.
`tesis.json` tenía un solo commit en toda su historia, el del día que se construyó la feature.

No se podía commitear a secas: la web (`web/api/tesis.ts`) escribe el mismo archivo pegándole
directo a la API de GitHub, y el paso de push se rearma sobre `origin/main` — copiar encima la
versión de la corrida habría borrado cualquier tesis escrita mientras el recolector trabajaba.

Entró `tesis.fusionar()` (+ `collector/fusionar_tesis.py`, que lo corre el workflow justo
después del `git reset --hard origin/main`): manda el archivo del repo, y del lado del
recolector se toman **solo** lecturas nuevas —deduplicadas por periodo/fecha/fuente/valor— y
el paso a `"rota"` ante una lectura roja. Umbrales, texto y métrica **nunca** se copian, así
que la tesis sigue siendo inmutable (regla dura de Fase 7); tampoco se toca una tesis ya
cerrada ni se revive una que el usuario borró desde la web. 8 tests nuevos, suite en 191.
Verificado en un run real: el paso imprime `tesis: N tesis, M lectura(s) nueva(s)`.

### 5. Lo del 24 de agosto, todavía sin mirar

Sigue igual que como quedó esa noche — José no lo ha visto. Antes de picar código nuevo,
preguntarle:

- **Rango "10A" del gráfico**: ¿se lee bien el eje rotulando año por medio? (Confirmado el 27:
  `daily.json` ya trae la clave `10A`, 522 puntos por ticker, así que el botón ya dibuja.)
- **Puntos de color por métrica**: ¿los umbrales le hacen sentido, sobre todo qué quedó ámbar
  vs. rojo? (Ámbar = elecciones de perfil: valoración cara, deuda alta, volatilidad. Rojo =
  "pierde plata o se está encogiendo".)
- **Simulador a dos cards por fila** en desktop.
- **Simulador en general**: nunca lo usó. Comprar algo de la watchlist y algo del Radar,
  vender una fracción. Falta también que corra por primera vez el cron del aporte mensual
  (día 1), o confirmar que el archivo semilla alcanza mientras tanto.
- **"Mi inversión"**: comprar/vender/editar/borrar con la clave real. El flujo completo solo
  se probó con clave incorrecta (401) porque acá no se tiene el `WATCHLIST_EDIT_KEY` real.
- Los recuadros "HOY"/"TU POSICIÓN" del header y el contraste del tooltip del gráfico.

### 6. Sin empezar, esperando que las pida explícitamente

- **Contexto de métricas, iteración 2 con Gemini.** Sin cambios.
- **Buscador de data avanzada para cualquier ticker.** Conversarlo con calma antes de picar
  código.
- **Extender "métricas avanzadas" completas al Radar.** Sin confirmar.
- **Puntaje o veredicto agregado por ticker** (sumar las señales por métrica en un "7 de 10").
  Sigue **prohibido sin preguntar primero**: choca con la regla dura del Radar. La señal por
  métrica del 24 es hasta donde se puede llegar sin esa conversación. Si lo vuelve a pedir:
  señalar el choque, preguntar, y documentar acá si dice que sí.

### 7. Pasada de debug del 28-08 — cinco bugs arreglados y pusheados

José pidió "debuggea, revisa si hay bugs". Ninguno lo había reportado él; salieron de leer
el código nuevo de Telegram y el workflow. Todos verificados en un run real
(`workflow_dispatch` 33215396115, verde en 1m11s) y en `main`:

- `38bfb39` — **un aviso de Telegram roto tumbaba la corrida entera.** `alertas.revisar()`
  se llamaba sin protección al final de `main()`; con el paso en rojo el workflow se saltea
  el push y `daily.json` nunca llega al repo. Mismo síntoma que el punto 2, otra causa. Era
  contradecir una regla que CLAUDE.md ya declaraba ("nunca tumba una corrida por un aviso").
- `88801a6` — **un rebote fuerte no avisaba.** El antiduplicado comparaba valor absoluto:
  un ticker que abría −5,2% y rebotaba a +6,0% quedaba callado porque `6 < 5,2 + 5`. Ahora
  dar vuelta el signo reinicia la comparación.
- `30c741f` — `pct(0.0)` devolvía `−0,0%`: un día plano se leía como caída.
- `132fc6a` — **el recorte a 4.096 caracteres provocaba el mismo 400 que quería evitar**:
  cortaba a lo bruto y partía una etiqueta o dejaba un `<b>` sin cerrar. Ahora corta en
  borde de bloque o de línea y cierra lo que quedó abierto.
- `47f9497` — el paso `frescura` tomaba el exit code de `tee`, no el de python: un crash
  del script habría dejado `correr` vacío y el run **en verde sin recolectar nada**.
  `set -o pipefail`.

Y `5e14ced` (pedido por José en la misma sesión): **el resumen matutino avisa arriba de todo
cuando `daily.json` está viejo.** Pasadas 3 horas abre con "⚠️ Estos precios son de hace N
horas/días". Antes, un recolector caído producía un mensaje idéntico al normal — sin
ninguna señal. El umbral (`HORAS_PARA_AVISAR` en `collector/resumen_telegram.py`) se eligió
así: el recolector corre cada hora todos los días, así que un snapshot sano tiene menos de
una hora; 3 h ya no es "el mercado está cerrado", es "nadie está recolectando".

Ojo con lo de arriba a la luz del punto 2: con los huecos de 5-6 h que hay ahora, **es
esperable que José empiece a ver el ⚠️**. Si lo reporta, no es un falso positivo — es el
aviso funcionando y contando el problema del cron. La suite quedó en **205 tests**.
