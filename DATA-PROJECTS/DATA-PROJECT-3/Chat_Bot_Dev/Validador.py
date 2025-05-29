from Estado import EstadoAgente
from langchain_core.messages import HumanMessage, SystemMessage
from configuration import setup_llm

llm, config = setup_llm()

def val_input_con_llm(state: EstadoAgente) -> EstadoAgente:
    entrada = state["mensajes"][-1]
    prompt = """
    Eres un asistente médico.

    ¿Esto parece una descripción válida de síntomas físicos o condiciones de salud?
    Responde solo con "sí" si es un texto clínico válido, y "no" si no tiene sentido médico.
    """
    content_prompt = [
        SystemMessage(content=prompt),
        HumanMessage(content=entrada),
    ]
    respuesta = llm.invoke(content_prompt, config).content.lower().strip()
    if "sí" in respuesta:
        state["input_valido"] = True
    else:
        state["input_valido"] = False
    return state