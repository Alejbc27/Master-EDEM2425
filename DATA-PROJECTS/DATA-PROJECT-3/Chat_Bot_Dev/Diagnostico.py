import requests
from Estado import EstadoAgente
from configuration import setup_infermedica_headers

HEADERS = setup_infermedica_headers()


def hacer_diagnostico(state: EstadoAgente) -> EstadoAgente:

    state["pasos"] += 1
    if state["pasos"] > 8:
        state["should_stop"] = True
        return state
    else:
        response = requests.post(
            "https://api.infermedica.com/v3/diagnosis",
            headers=HEADERS,
            json={
                "age": {"value": 24, "unit": "year"},
                "sex": "male",
                "evidence": state["evidencia"],
                "context": ["string"],
                "include_tokens": True,
                "correct_spelling": True,
                "concept_types": ["symptom"],
            },
        )
        resultado = response.json()
        # state['diagnostico'] = resultado
        state["should_stop"] = resultado.get("should_stop", False)

        # Guardar condiciones ordenadas por probabilidad
        condiciones = resultado.get("conditions", [])
        condiciones.sort(key=lambda x: x["probability"], reverse=True)
        state["condiciones"] = condiciones

        # Guardar próxima pregunta sugerida
        preguntas = resultado.get("question", {})
        if preguntas:
            state["pregunta_actual"] = preguntas
            state["situacion"] = "diagnosticar"
        else:
            state["pregunta_actual"] = None
    return state
