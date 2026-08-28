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

## Pendiente (al cerrar la sesión del 2026-08-27, ya de madrugada del 28)

**Contexto de arranque:** José sigue sin haber visto nada de lo del 24 *ni* de lo del 27 —
lo dijo explícitamente al cerrar esta sesión ("no he leído nada de lo que hemos hecho").
Todo lo de abajo está commiteado y pusheado. No asumir que algo está aprobado para seguir
sin que él lo mire y confirme primero.

### 1. Lo primero al retomar: los dos secrets de Telegram

Nada de lo que se construyó esta sesión llega al celular hasta que José haga esto. Son
cinco minutos y es 100% de él, no se puede hacer desde acá:

1. En Telegram, hablarle a **@BotFather** → `/newbot` → elegir nombre. Devuelve un token
   tipo `8123456789:AAH...`.
2. Escribirle *algo* al bot recién creado (un "hola") — sin eso Telegram no deja que el bot
   inicie la conversación.
3. Sacar el chat id: abrir `https://api.telegram.org/bot<TOKEN>/getUpdates` en el navegador
   y copiar `result[0].message.chat.id`.
4. Repo → Settings → Secrets and variables → Actions → New repository secret, dos veces:
   `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
5. Opcional: en la pestaña **Variables** (no Secrets), `APP_URL` con la URL de Vercel, para
   que el resumen traiga el link "Ver todo en la app". La URL no está en el repo — hay que
   preguntársela.

Para probar sin esperar: Actions → "Resumen por Telegram (mañana)" → Run workflow. Ya se
corrió así el 2026-08-28T03:42 **sin** los secrets y salió limpio (`Telegram sin configurar
(falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID)`, exit 0) — o sea el workflow está validado
contra la infra real, lo único que falta son las credenciales.

### 2. GitHub dejó de disparar los cron — arreglado a medias, SIN VERIFICAR

Esto es lo que motivó toda la sesión: José vio que la app llevaba horas sin actualizarse.

**Diagnóstico (con datos, no con corazonada):** GitHub está botando los eventos `schedule`
de este repo. Hasta el 26-08 14:00 UTC el recolector corría casi cada hora; después se
degradó (16, 18, 21 → dos runs el 27 → nada). El último run *programado* de cualquier
workflow fue el 2026-08-27T13:28 UTC; a las 03:41 UTC del 28 seguía sin haber ninguno, o sea
14+ horas de silencio total, incluidos los daily de Fintual y Amigos. Descartado uno por uno:
no es el collector (todos los runs que sí corrieron terminaron `success`), no es cuota (repo
público, minutos ilimitados), no son los workflows (los cinco `active`), no es un incidente
(githubstatus.com decía Actions operacional). Y los runs que sí llegaban arrancaban a minutos
random (:12, :28, :37, :46, :54) en vez de :00 — la firma clásica de la cola de Actions.

**Lo que se hizo** (commit `2b3a851`): ninguno de los cinco workflows arranca ya en :00 ni
:30, los dos minutos más congestionados de GitHub. Y `daily.yml` pasó a tener dos horarios
por hora — `:17` principal y `:47` respaldo — donde el respaldo sale en ~10 segundos si
`data/daily.json` tiene menos de 45 minutos (paso `frescura`). No son dos recolecciones:
el tramo horario de `historico_precios.json` guarda todos los puntos que le llegan, así que
recolectar dos veces por hora duplicaría ese archivo (5,1 MB hoy) a cambio de nada.

**Ojo — esto todavía no se probó que funcione.** Entre el push (2026-08-27 ~22:15 UTC) y el
cierre de sesión (03:41 UTC del 28) no se disparó **ni un solo** cron, así que no hay
evidencia de que cambiar el minuto ayude. Importante para no confundirse mañana: los runs
programados ya estaban muertos *antes* de tocar los YAML (último: 13:28 UTC), así que el
silencio no lo causó este cambio.

**Qué hacer al retomar, en orden:**

- Mirar `gh run list --limit 20` y ver si hubo runs con `event=schedule` durante la noche.
- Si volvieron: listo, el cambio de minuto alcanzó. Nada más que hacer.
- Si **siguen sin correr**: la respuesta es la opción que quedó en la manga, un **disparador
  externo** — un cron gratis fuera de GitHub (cron-job.org u otro) que llame por API al
  `workflow_dispatch` de `daily.yml`. `workflow_dispatch` no sufre este throttling, se
  comprobó esta misma sesión (todos los disparos manuales corrieron al toque). Cuesta $0 pero
  mete una pieza de terceros y un PAT viviendo fuera del repo, así que **preguntarle antes**:
  ya se le ofreció el 27 y eligió empezar por lo barato.

De paso se endureció el push de `daily.yml`: antes hacía `git pull --rebase` a secas y si dos
runs se pisaban, el segundo moría con un conflicto en `daily.json` (pasó de verdad el 27,
disparando dos runs manuales a la vez). Ahora el snapshot recién generado gana: se rearma
sobre `origin/main` y reintenta hasta 3 veces.

Para desatascar la data esa noche se corrió el recolector a mano — `daily.json` quedó en
2026-08-27T21:26 UTC (17:26 Chile).

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

### 4. Bug encontrado de paso, sin arreglar (necesita su decisión)

`collector/main.py` llama a `_guardar_tesis()` en cada corrida, pero `daily.yml` nunca
commitea `data/tesis.json` — solo `daily.json`, `historico_precios.json` y ahora
`alertas_enviadas.json`. O sea: cada revisión automática de tesis que hace el collector
(`_revisar_tesis_ticker`, el semáforo pasando a ámbar o a roto) se escribe en el runner y se
tira a la basura. Las tesis que crea José desde la web sí persisten, porque `web/api/tesis.ts`
escribe directo contra la API de GitHub. Confirmado: `tesis.json` tiene un solo commit en toda
su historia, el del día que se construyó la feature.

No se tocó porque es Fase 7 y la regla dura dice que una tesis es inmutable — hay que
entender bien qué campos toca `_revisar_tesis_ticker` antes de empezar a persistirlos.
Preguntarle a José si quiere que se arregle.

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
