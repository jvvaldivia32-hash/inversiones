# Dashboard de Inversiones y Actualidad

Una URL que abre en el celular cada mañana: qué pasó en el mundo, en Chile, y con las
inversiones. Datos duros con fuente verificable. Costo de operación: $0/mes.

Arquitectura, fases y modelo de datos completos en `docs/plan-app-inversiones.md`.

```
collector/   Python, corre en GitHub Actions (cron diario). Escribe data/daily.json.
web/         React + Vite. Solo lee data/daily.json, deploy en Vercel.
```

Estado: Fase 0 (esqueleto visual con datos de prueba).
