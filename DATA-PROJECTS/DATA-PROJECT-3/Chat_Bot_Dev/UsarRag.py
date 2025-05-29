import requests
import logging
import os
import json
from Estado import EstadoAgente
from configuration import setup_llm, setup_infermedica_headers
from langchain_core.messages import SystemMessage, HumanMessage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

llm, config = setup_llm()

def _traducir_condiciones(condiciones_usuario: str) -> str | None:
    try:
        traduccion_prompt = [
            SystemMessage(
                content=(
                    "Eres un experto traductor médico. Traduce la siguiente consulta del usuario al español médico técnico."
                    "Devuelve solo la traducción como una cadena de texto, sin explicaciones adicionales."
                )
            ),
            HumanMessage(content=condiciones_usuario),
        ]
        traduccion_response = llm.invoke(traduccion_prompt, config)
        traduccion = traduccion_response.content.lower().strip()
        logger.info(f"Traducción para RAG: {traduccion}")
        return traduccion
    except Exception as e:
        logger.error(f"Error durante la traducción: {e}")
        return None


def _buscar_documentos_rag(
    rag_api_url: str, collection_name: str, query: str, limit: int = 2
) -> dict | None:
    body = {"collection_name": collection_name, "query": query, "limit": limit}
    try:
        response = requests.post(
            f"{rag_api_url}/search",
            headers={"Content-Type": "application/json"},
            json=body,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la solicitud a la API RAG: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar la respuesta JSON de la API RAG: {e}")
    return None


def _generar_informe_llm(
    consulta_traducida: str, contexto_documentos: str
) -> str | None:
    try:
        informe_prompt_messages = [
            SystemMessage(
                content=(
                    "Eres un asistente médico experto. Basándote en la siguiente consulta del usuario y la información de los documentos recuperados, "
                    "genera un informe conciso sobre las posibles causas y soluciones/tratamientos para la condición mencionada en la consulta. "
                    "Sé claro y utiliza un lenguaje comprensible. Si la información no es suficiente, indícalo. "
                    "No inventes información que no esté en los documentos. Estructura tu respuesta claramente."
                )
            ),
            HumanMessage(
                content=f"Consulta del usuario: {consulta_traducida}\n\n"
                f"Información de documentos relevantes:\n{contexto_documentos}"
            ),
        ]
        informe_response = llm.invoke(informe_prompt_messages,config)
        informe_generado = informe_response.content
        logger.info(f"Informe generado por LLM con RAG: {informe_generado[:200]}...")
        return informe_generado
    except Exception as e:
        logger.error(f"Error al generar informe con LLM: {e}")
        return None


def usar_rag(state: EstadoAgente) -> EstadoAgente:
    collection_name = "medical_articles"
    rag_api_url = "https://vector-database-api-710866946885.europe-west1.run.app"

    condiciones_originales = ", ".join([cond.get("name", "") for cond in state["condiciones"] if "name" in cond])

    traduccion = _traducir_condiciones(condiciones_originales)
    search_results = _buscar_documentos_rag(
        rag_api_url, collection_name, traduccion, limit=2
    )

    if search_results.get("status") == "success" and search_results.get("results"):
        documentos = search_results["results"]

        contexto_documentos = ""
        if len(documentos) > 0:
            doc1_meta = documentos[0].get("metadata", {})
            doc1_content = documentos[0].get("content", "N/A")
            contexto_documentos += f"Documento 1:\nTítulo: {doc1_meta.get('title', 'N/A')}\nContenido: {doc1_content}\n\n"
        if len(documentos) > 1:
            doc2_meta = documentos[1].get("metadata", {})
            doc2_content = documentos[1].get("content", "N/A")
            contexto_documentos += f"Documento 2:\nTítulo: {doc2_meta.get('title', 'N/A')}\nContenido: {doc2_content}\n\n"

        informe_generado = _generar_informe_llm(traduccion, contexto_documentos)
        state["informe"] = informe_generado

    else:
        error_message = search_results.get(
            "message", "Respuesta no exitosa de la API RAG"
        )
        details = search_results.get("details", "")
        logger.error(
            f"Error en la respuesta de la API RAG: {error_message}. Detalles: {details}"
        )

    return state
