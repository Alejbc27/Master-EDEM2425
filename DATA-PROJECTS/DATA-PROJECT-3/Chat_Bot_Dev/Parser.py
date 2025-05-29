import requests
from Estado import EstadoAgente
from configuration import setup_llm, setup_infermedica_headers
from langchain_core.messages import HumanMessage, SystemMessage

llm, config = setup_llm()
HEADERS = setup_infermedica_headers()


def parsear_sintomas(state: EstadoAgente) -> EstadoAgente:

    entrada = state["mensajes"][-1]

    prompt = """
    Eres un asistente médico.

    Tu dever es traducir el texto al inglés médico para que la API de Infermedica lo entienda.
    Por favor, traduce el texto a inglés médico y devuélvelo como una cadena de texto.
    """
    content_prompt = [
        SystemMessage(content=prompt),
        HumanMessage(content=entrada),
    ]

    respuesta = llm.invoke(content_prompt, config).content.lower().strip()

    response = requests.post(
        "https://api.infermedica.com/v3/parse",
        headers=HEADERS,
        json={
            "age": {"value": 24, "unit": "year"},
            "sex": "male",
            "text": respuesta,
            "context": ["string"],
            "include_tokens": True,
            "correct_spelling": True,
            "concept_types": ["symptom"],
        },
    )
    parsed = response.json()

    evidencia = []
    for mention in parsed.get("mentions", []):
        evidencia.append(
            {"id": mention["id"], "choice_id": "present", "source": "initial"}
        )

    state["evidencia"].extend(evidencia)