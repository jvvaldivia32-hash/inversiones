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
> `--acento` desvaneciendo a transparente — no un color nuevo. Es la única excepción
> decorativa a esta regla. No la uses como precedente para agregar color en otro lado sin
> preguntar primero.

**Radar:** solo muestra candidatos con sus datos. Nunca genera texto tipo "deberías
comprar". Los descartados se muestran siempre, con el motivo — no se ocultan.

**Tesis (Fase 7+):** inmutable una vez escrita. Editar = cerrar la vieja y crear una nueva.
Nunca sobreescribir los umbrales de una tesis existente.

## Stack

Recolector: Python, corre en GitHub Actions por cron. Visor: React + Vite, deploy en
Vercel. Un repo, dos carpetas (`collector/`, `web/`). El visor sigue sin llamar APIs en vivo
para *mostrar* datos — precios, noticias, fundamentales vienen únicamente de
`data/daily.json`. La única excepción es un camino de escritura acotado: `web/api/
watchlist.ts`, una función serverless de Vercel que edita `watchlist.txt` vía la API de
GitHub para el panel de la watchlist. El token de GitHub con permiso de escritura vive solo
en esa función (variable de entorno del lado del servidor) — el navegador nunca lo tiene.

## Secrets

Nunca hardcodear keys en el código. Todo vía variables de entorno / GitHub Secrets:
`GEMINI_API_KEY`, `FINNHUB_KEY`, `SEC_USER_AGENT`, `BCCH_USER`, `BCCH_PASS`,
`GITHUB_WRITE_TOKEN` (fine-grained PAT, solo permiso Contents R/W sobre este repo, usado por
`web/api/watchlist.ts`), `WATCHLIST_EDIT_KEY` (clave compartida que protege el POST de ese
endpoint — no es autenticación real, es el candado mínimo para una app de un solo usuario).
