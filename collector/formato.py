"""Números como se escriben en Chile, para los mensajes de Telegram.

Vive aparte porque lo usan tanto las alertas de movimiento como el resumen de la mañana, y
`from alertas import _num` sería importar un privado de otro script.
"""


def num(valor: float, decimales: int = 2) -> str:
    """Separador de miles con punto y decimales con coma: 1.234,56."""
    entero, _, dec = f"{valor:,.{decimales}f}".partition(".")
    entero = entero.replace(",", ".")
    return f"{entero},{dec}" if dec else entero


def pct(valor: float) -> str:
    # Menos tipográfico (−), no guion: en el chat se distingue mejor del guion de un rango.
    signo = "+" if valor > 0 else "−"
    return f"{signo}{num(abs(valor), 1)}%"
