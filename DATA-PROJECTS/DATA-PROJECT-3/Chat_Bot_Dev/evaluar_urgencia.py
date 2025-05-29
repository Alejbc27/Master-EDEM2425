import requests
from Estado import EstadoAgente
from configuration import setup_infermedica_headers

HEADERS = setup_infermedica_headers()

def evaluar_urgencia(state: EstadoAgente) -> EstadoAgente:
    try:
        response = requests.post(
            'https://api.infermedica.com/v3/triage',
            headers=HEADERS,
            json={
                "sex": "male",
                "age": {"value": 24,"unit": "year"},
                "evidence": state["evidencia"]
            }
        )

        response.raise_for_status()
        resultado = response.json()

        state["urgencia"] = resultado.get("urgencia", "self_care")

    except Exception as e:
        print(f"Error evaluando urgencia: {e}")
        state["urgencia"] = "self_care"

    return state