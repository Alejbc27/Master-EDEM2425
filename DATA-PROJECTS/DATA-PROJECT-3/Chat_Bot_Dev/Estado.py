
from typing import TypedDict, List, Optional

class EstadoAgente(TypedDict):
    situacion: str            # Situación actual del agente, Ayuda a decidir que nodo ejecutar
    mensajes: List          # Historial de mensajes usuario-agente
    evidencia: List[dict]         # Síntomas detectados (evidence)
    condiciones: List[dict]       # Lista de condiciones posibles {id, name, probabilidad}
    pregunta_actual: Optional[dict]  # Pregunta sugerida (question) por diagnosis
    lista_preguntas: Optional[dict]  # Pregunta sugerida (question) por diagnosis
    diagnostico: Optional[dict]   # Diagnóstico completo de la API
    should_stop: bool              # Si ya podemos parar de preguntar
    urgencia: Optional[str]       # Nivel de urgencia ('emergency', 'consultation', etc.)
    respuesta_usuario: Optional[str] # Ultima respuesta del usuario (No ecuentro uso para esta opcion por ahora)
    pasos: int                # Pasos realizados en diagnosis
    input_valido: Optional[bool]    # Si la respuesta del usuario es valida o no para el Parser
    informe: Optional[str]        # Informe generado por el LLM
