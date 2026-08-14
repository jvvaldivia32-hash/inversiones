import json
import urllib.error
import urllib.request

# Confirmado a mano contra el spec real (curl a https://fintual.cl/api-docs/v1/swagger.json,
# no un blog viejo) y probado en vivo por el usuario: /goals es lo único privado que existe
# — nombre y saldo (`nav`) actual por meta de inversión. No hay endpoint de rentabilidad ni
# de portafolio total ni de histórico de aportes/retiros — el saldo total se arma sumando
# los `nav` acá afuera, y "rentabilidad" queda fuera de alcance a propósito (mezclaría
# ganancia real con depósitos nuevos sin poder distinguirlos).
BASE_URL = "https://fintual.cl/api"

# Cloudflare (delante de la API de Fintual) bloquea el User-Agent por defecto de
# urllib ("Python-urllib/3.x") con 403 — probado en vivo: el mismo request con un
# User-Agent de navegador sí llega a la app y devuelve el 401 real. Mismo gotcha que
# yahoo.py (Yahoo también rechaza requests sin UA de navegador), esta vez encontrado
# recién al probar contra la cuenta real, no en desarrollo local.
USER_AGENT = "Mozilla/5.0 (inversiones-recolector)"


class FintualError(Exception):
    pass


def _request(ruta: str, email: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{ruta}",
        headers={"X-User-Email": email, "X-User-Token": token, "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise FintualError(f"Fintual {ruta} respondió {e.code}") from e
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        # TimeoutError no es subclase de URLError — mismo gotcha ya visto en
        # gemini.py/yahoo.py/edgar.py/prices.py.
        raise FintualError(f"Fintual {ruta} no respondió: {e}") from e


def obtener_goals(email: str, token: str) -> list[dict]:
    """[{"id", "nombre", "saldo"}] por cada meta de inversión activa. El token no tiene
    expiración documentada en el spec ni en los headers de respuesta reales — si algún
    día deja de funcionar, esto levanta FintualError como cualquier otra fuente; quien
    llama decide degradar (conservar el valor anterior), mismo criterio que el resto del
    collector."""
    if not email or not token:
        raise FintualError("FINTUAL_USER_EMAIL/FINTUAL_USER_TOKEN no están seteadas")

    data = _request("/goals", email, token)
    resultado = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        resultado.append(
            {
                "id": item.get("id"),
                "nombre": attrs.get("name"),
                "saldo": attrs.get("nav"),
            }
        )
    return resultado
