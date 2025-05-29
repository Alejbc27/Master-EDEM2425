from Validador import val_input_con_llm

from Parser import parsear_sintomas
from Diagnostico import hacer_diagnostico
from evaluar_urgencia import evaluar_urgencia
from Reservar_cita import reservar_cita
from Estado import EstadoAgente
from UsarRag import usar_rag
import json

from typing import Literal

# ---Descrivimos los nodos de la grafo---


def inicio(state):
    """
    Este nodo solo existe para comprobar a que dodo se tiene que enviar el estado.
    """
    print("Estado inicial")
    return state


def end(state):
    """
    Este nodo solo existe para ser el nodo final.
    """
    print("Estado final")
    return state


def nodo_validacion(state):
    """
    Validamos el mensage del usuario para saber si podemos enviarlo a parser.
    """
    print("Validando el mensaje del usuario")
    val_input_con_llm(state)
    return state


def nodo_parser(state):
    """
    Parseamos el mensaje del usuario para obtener los sintomas.
    """
    print("Parseando el mensaje del usuario")
    parsear_sintomas(state)
    return state


def ejecutar_diagnostico(state):
    """
    Hacemos el diagnosticar a partir de los sintomas.
    """
    print("Haciendo el diagnosticar")
    hacer_diagnostico(state)
    return state


def nodo_urgencia(state):
    """
    Evaluamos la urgencia del paciente.
    """
    print("Evaluando la urgencia del paciente")
    #evaluar_urgencia(state)
    state["situacion"]="rag"
    return state


def nodo_reserva(state):
    """
    Reservamos la cita con el especialista.
    """
    print("Reservando la cita con el especialista")
    reservar_cita(state)
    return state


def nodo_rag(state):
    """
    Hacemos la llamada a la API de RAG para obtener el informe.
    """
    print("Haciendo la llamada a la API de RAG")
    usar_rag(state)
    return state


# ---Descrivimos los Edjes de la grafo---


def salir_inicio(
    state,
) -> Literal["validacion", "diagnosticar", "evaluar urgencia", "reserva", "ERROR","rag"]:
    """
    Este edje se encarga de ir al nodo de validacion.
    """
    print(f"Estado en salir_inicio: {json.dumps(state, indent=4)}")
    if state["situacion"] == "validacion":
        return "validacion"
    elif state["situacion"] == "diagnosticar":
        return "diagnosticar"
    elif state["situacion"] == "evaluar urgencia":
        return "evaluar urgencia"
    elif state["situacion"] == "reserva":
        return "reserva"
    elif state["situacion"] == "rag":
        return "rag"
    else:
        return "ERROR"


def salir_val(state) -> Literal["parser", "end"]:
    """
    Este edje decide a donde ir tras val.
    """
    if state["input_valido"] == True:
        return "parser"
    return "end"


def salir_parser(state) -> Literal["diagnosticar"]:
    """
    Este edje manda los resultados de parser a diagnosticar para obtener la pregunta.
    """
    return "diagnosticar"


def salir_diagnostico(state) -> Literal["evaluar urgencia", "end"]:
    """
    Este edje manda los resultados de diagnosticar a:
        -END para continuar las preguntas.
        -evaluar urgencia para evaluar al nodo evaluar urgencia.
    """
    if state["should_stop"] == True:
        return "evaluar urgencia"
    return "end"


def salir_urgencia(state) -> Literal["end"]:
    """
    Este edje manda los resultados de evaluar urgencia a:
        -End para esperar la respuesta del usuario.
    """
    return "end"


def salir_reserva(state) -> Literal["end"]:
    """
    Este edge manda los resultado de reserva a rag
    """
    return "end"


def salir_rag(state) -> Literal["end"]:
    """
    Este edje manda los resultados de rag a end.
    """
    return "end"


# ---Definimos la grafo---
from langgraph.graph import StateGraph

workflow = StateGraph(EstadoAgente)

# añadir nodos
workflow.add_node("inicio", inicio)
workflow.add_node("validacion", nodo_validacion)
workflow.add_node("parser", nodo_parser)
workflow.add_node("diagnosticar", ejecutar_diagnostico)
workflow.add_node("evaluar urgencia", nodo_urgencia)
workflow.add_node("reserva", nodo_reserva)
workflow.add_node("rag", nodo_rag)
workflow.add_node("end", end)

# seleccionar punto de inicio
workflow.set_entry_point("inicio")

# añadir edges
workflow.add_conditional_edges(
    "inicio",
    salir_inicio,
    {
        "validacion": "validacion",
        "diagnosticar": "diagnosticar",
        "urgencia": "evaluar urgencia",
        "reserva": "reserva",
        "ERROR": "end",
    },
)
workflow.add_conditional_edges(
    "validacion",
    salir_val,
    {
        "parser": "parser",
        "end": "end",
    },
)
workflow.add_edge("parser", "diagnosticar")
workflow.add_conditional_edges(
    "diagnosticar",
    salir_diagnostico,
    {
        "evaluar urgencia": "evaluar urgencia",
        "end": "end",
    },
)

workflow.add_edge("evaluar urgencia", "end")

workflow.add_edge("reserva", "rag")
workflow.add_edge("rag", "end")

# seleccionar punto de salida
workflow.set_finish_point("end")

grafo = workflow.compile()
