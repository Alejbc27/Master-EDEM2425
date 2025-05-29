import random
import uuid
import json
import sys
from typing import TypedDict, List, Dict, Optional
from google.cloud import firestore 
from utils import get_conn 

class EstadoAgente(TypedDict):
    patient_id: int
    mensajes: List[Dict[str, str]]
    evidencia: List[str]  # JSON serializado en strings
    condiciones: List[Dict[str, object]]
    pregunta_actual: List[str]
    lista_preguntas: Optional[Dict[str, Dict[str, object]]]
    diagnostico: Optional[str]  # ahora JSON serializado como string
    should_stop: bool
    urgencia: Optional[str]
    respuesta_usuario: Optional[str]
    pasos: int
    input_valido: Optional[bool]
    informe: Optional[str]

# Valores base
SINTOMAS = [
    "dolor de cabeza", "náuseas", "fiebre", "tos",
    "dolor de garganta", "fatiga", "mareo", "fotofobia"
]
CONDICIONES = [
    "Cefalea tensional", "Migraña", "Sinusitis",
    "Gripe", "Resfriado común", "COVID-19"
]
PREGUNTAS = [
    "¿Experimentas náuseas o vómitos junto con el dolor de cabeza?",
    "¿La intensidad del dolor aumenta con la luz o el ruido?",
    "¿Has tenido fiebre recientemente?",
    "¿Has tomado algún medicamento para el dolor?"
]
URGENCIAS = ["emergency", "consultation", "routine"]
MSJ_U = [
    "Me duele la cabeza desde esta mañana.",
    "Tengo fiebre y escalofríos.",
    "Siento mucha fatiga.",
    "¿Qué puedo tomar para el dolor?",
    "No he dormido bien en dos noches.",
    "Tengo tos seca constante."
]
MSJ_A = [
    "¿Desde cuándo comenzaron los síntomas?",
    "¿Has notado algún desencadenante?",
    "¿Cómo calificarías la intensidad del dolor de 1 a 10?",
    "Voy anotando los síntomas para el diagnóstico."
]

def generate_estado_agente() -> EstadoAgente:
    # Historial de mensajes alternados
    mensajes = [
        {"sender": "user", "message": random.choice(MSJ_U)} if i % 2 == 0
        else {"sender": "agent", "message": random.choice(MSJ_A)}
        for i in range(random.randint(3, 7))
    ]

    # Construcción de objetos de evidencia
    evidencia_objs = [
        {
            "id": f"s_{uuid.uuid4().hex[:6]}",
            "name": s,
            "choice_id": random.choices(["present", "absent", "unknown"], weights=[.5, .3, .2])[0],
            "probabilidad": round(random.uniform(.2, .9), 2)
        }
        for s in random.sample(SINTOMAS, random.randint(2, 5))
    ]
    # Serializar cada objeto de evidencia a string JSON
    evidencia = [json.dumps(e, ensure_ascii=False) for e in evidencia_objs]

    # Condiciones posibles y normalización de probabilidades
    probs = [random.random() for _ in CONDICIONES]
    total = sum(probs)
    condiciones = [
        {
            "id": f"c_{uuid.uuid4().hex[:6]}",
            "name": n,
            "probabilidad": round(p / total, 2)
        }
        for n, p in zip(CONDICIONES, probs)
    ]

    # Pregunta actual y lista de siguientes preguntas con probabilidades
    pd = random.sample(PREGUNTAS, 4)
    pregunta_actual = [pd[0]]
    lista_preguntas = {
        f"p_{i}": {
            "question": q,
            "probabilidad": round(random.uniform(.1, .9), 2)
        }
        for i, q in enumerate(pd[1:], 1)
    }

    # Diagnóstico basado en la condición de mayor probabilidad (objeto)
    mejor = max(condiciones, key=lambda x: x["probabilidad"])
    diagnostico_obj = {
        "id": mejor["id"],
        "name": mejor["name"],
        "confidence": mejor["probabilidad"],
        "recomendacion": (
            "Se sugiere evaluación presencial."
            if mejor["probabilidad"] > .7
            else "Monitorear síntomas y seguir consulta virtual."
        )
    }
    # Generar informe antes de serializar diagnostico
    pasos = len(mensajes)
    informe = (
        f"Tras {pasos} intercambios, síntomas principales: " +
        ", ".join(e['name'] for e in evidencia_objs if e['choice_id'] == 'present') +
        f". Diagnóstico probable: {diagnostico_obj['name']} (confianza {diagnostico_obj['confidence']})."
    )
    # Serializar diagnostico a string JSON
    diagnostico = json.dumps(diagnostico_obj, ensure_ascii=False)

    input_valido = random.choice([True] * 4 + [False])

    return EstadoAgente(
        # patient_id se inyecta externamente antes de enviar
        mensajes=mensajes,
        evidencia=evidencia,
        condiciones=condiciones,
        pregunta_actual=pregunta_actual,
        lista_preguntas=lista_preguntas,
        diagnostico=diagnostico,
        should_stop=diagnostico_obj["confidence"] > .8 or pasos >= 10,
        urgencia=random.choice(URGENCIAS),
        respuesta_usuario=(mensajes[-1]["message"]
                           if mensajes[-1]["sender"] == "user" else None),
        pasos=pasos,
        input_valido=input_valido,
        informe=informe
    )


def send_estado(collection_ref: firestore.CollectionReference, estado: EstadoAgente) -> None:
    """
    Inserta el dict en Firestore usando patient_id como doc ID.
    """
    pid = estado["patient_id"]
    collection_ref.document(str(pid)).set(estado)


def main():
    # 1) Conectamos a Firestore
    client = firestore.Client(project="data-project-3-457210")
    coleccion = client.collection("patients-db-dp3")

    # 2) Recuperamos TODOS los patient_id de PostgreSQL
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT patient_id FROM patient")
            patient_ids = [row[0] for row in cur.fetchall()]

    # 3) Para cada patient_id generamos y enviamos un estado
    for pid in patient_ids:
        estado = generate_estado_agente()
        estado["patient_id"] = pid   # ← inyectamos el ID aquí
        send_estado(coleccion, estado)
        print(f"✅ Estado enviado para patient_id = {pid}")


if __name__ == "__main__":
    main()
