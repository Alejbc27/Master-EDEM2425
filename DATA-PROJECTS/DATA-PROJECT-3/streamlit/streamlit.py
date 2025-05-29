import streamlit as st
import requests
import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def setup_llm():
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", temperature=0.3,
                                google_api_key=GOOGLE_API_KEY)
    config = {"configurable": {"thread_id": "1"}}
    return llm, config

llm, config = setup_llm()

def crear_pregunta(preg_items):
    opciones = ""
    for i, item in enumerate(preg_items):
        opciones += f"{i + 1}. {item['name']}"
        if i < len(preg_items) - 1:
            opciones += ", "
        else:
            opciones += " or "
    opciones += f"{len(preg_items) + 1}. None of the above."
    return opciones
# --- CSS Personalizado para Estilizar ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFFFFF; /* Fondo blanco */
    }
    /* Asegura que todo el texto dentro de la aplicación sea negro por defecto */
    body, p, div, span, label, input, textarea, .stMarkdown, .stText, .stButton, .stTextInput {
        color: #000000 !important; /* Texto negro para todos los elementos, fuerza con !important */
    }

    .stTextInput > div > div > input {
        background-color: #E6F3FF; /* Fondo de entrada azul claro */
        border: 1px solid #007BFF; /* Borde azul */
    }
    .stButton > button {
        background-color: #007BFF; /* Botón azul */
        color: #FFFFFF !important; /* Texto blanco en el botón, fuerza con !important */
        border-radius: 5px;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        cursor: pointer;
    }
    .stButton > button:hover {
        background-color: #0056b3; /* Azul más oscuro al pasar el ratón */
    }
    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .stChatMessage.user {
        background-color: #DCF8C6; /* Verde claro para los mensajes del usuario */
        text-align: right;
    }
    .stChatMessage.chatbot {
        background-color: #E6F3FF; /* Azul claro para los mensajes del chatbot */
        text-align: left;
    }
    /* Asegura que el texto dentro de los mensajes del chat sea negro */
    .stChatMessage p {
        color: #000000 !important; /* Fuerza el texto negro dentro de los mensajes del chat */
    }

    h1, h2, h3, h4, h5, h6 {
        color: #0056b3 !important; /* Azul más oscuro para los encabezados, fuerza con !important */
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("MediQuestAI ⚕️") # Se añadió un icono médico al título
backend_url = "http://127.0.0.1:8000/modificar_estado/"

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "chatbot",
                                     "content": "👋 ¿Podrías darme una descripción de tus síntomas?"}]
if "esperando_respuesta" not in st.session_state:
    st.session_state["esperando_respuesta"] = True

if "pedir_cita" not in st.session_state:
    st.session_state["pedir_cita"] = False
if "estado" not in st.session_state:
    st.session_state["estado"] = {
        "situacion": "validacion",
        "mensajes": [],
        "evidencia": [],
        "condiciones": [],
        "pregunta_actual":[],
        "lista_preguntas": {},
        "diagnostico": None,
        "should_stop": False,
        "urgencia": None,
        "respuesta_usuario": None,
        "pasos": 0,
        "input_valido": None,
        "informe": None
    }
if "num_opciones_actual" not in st.session_state:
    st.session_state["num_opciones_actual"] = 0

if "mini_preg" not in st.session_state:
    st.session_state["mini_preg"] = []

if "evidencia" not in st.session_state:
    st.session_state["evidencia"] = []


num_messages = len(st.session_state["messages"])

st.subheader("Conversación:")
for i in range(0, num_messages):
    message = st.session_state["messages"][i]
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_message = st.text_input(st.session_state.get("pregunta_actual", "Conversación:"), key="user_message")


def send_user_message():
    if st.session_state["user_message"]:  # Check if user_message is not empty
        if st.session_state["estado"]["situacion"] == "validacion":
            user_input = st.session_state["user_message"]
            st.session_state["messages"].append({"role": "user", "content": user_input})
            st.session_state["user_message"] = ""  # Clear input
            st.session_state["esperando_respuesta"] = False  # User has responded
            st.session_state["estado"]["mensajes"].append(user_input)
            try:
                response = requests.post(backend_url, json=st.session_state["estado"])
                response.raise_for_status()
                st.session_state["estado"] = response.json()

                if st.session_state["estado"]["input_valido"] is False:
                    st.session_state["messages"].append(
                        {"role": "chatbot",
                         "content": "Por favor, necesito información clara de sus síntomas para poder ayudarle"})
                    st.session_state["pregunta_actual"] = {}  # Reset to empty dict
                    st.session_state["esperando_respuesta"] = True
                elif st.session_state["estado"].get("pregunta_actual"):
                    st.session_state["estado"]["situacion"] = "diagnosticar"

            except requests.exceptions.RequestException as e:
                st.error(f"Error al conectar con el backend: {e}")
            except json.JSONDecodeError:
                st.error("Error al decodificar la respuesta del backend.")
            except requests.exceptions.HTTPError as e:
                st.error(f"Error del backend: {e}")

        if st.session_state["estado"]["situacion"] == "val_preg_simple" and st.session_state["estado"][
            "pregunta_actual"] is not None:
            user_input = st.session_state["user_message"]
            st.session_state["messages"].append({"role": "user", "content": user_input})
            st.session_state["user_message"] = ""
            st.session_state["esperando_respuesta"] = False

            st.session_state["estado"]["mensajes"].append(user_input)
            prompt_sistema = f"""
                Eres un asistente médico.Tu deber es asegurarte de que las respuestas de los usuarios se puedan clasificar como un sí, no o quizás de forma clara.
                En caso de que la respuesta no encaje de forma clara en una de estas 3 opciones responde REPETIR.
                En caso de que la respuesta sea claramente afirmativa responde con un SI.
                En caso de que la respuesta sea claramente negativa responde con un NO.
                Por último, si el usuario responde con un quizás claro responde QUIZAS
                                         """
            prompt = [
                SystemMessage(content=prompt_sistema),
                HumanMessage(content=user_input)
            ]
            respuesta = llm.invoke(prompt, config).content.lower().strip()

            situacion = ""
            if respuesta == "si":
                situacion = "present"
            elif respuesta == "no":
                situacion = "absent"
            elif respuesta == "quizas":
                situacion = "unknown"
            else:
                respuesta = "Disculpa, no he entendido tu respuesta. Por favor, responde con un sí, no o quizás."
                st.session_state["messages"].append({"role": "chatbot", "content": respuesta})
                st.session_state["esperando_respuesta"] = True

            if situacion in ["present", "absent", "unknown"]:
                evidencia = []
                evidencia.append({
                    'id': st.session_state["estado"]['pregunta_actual']["items"][0]['id'],
                    'choice_id': situacion,
                    'source': 'suggest'
                })

                st.session_state["estado"]['evidencia'].extend(evidencia)
                st.session_state["estado"]["lista_preguntas"][
                    st.session_state["estado"]['pregunta_actual']["text"]] = {
                    st.session_state["estado"]['pregunta_actual']["items"][0]['id']: situacion}

                st.session_state["estado"]['pregunta_actual'] = None
                st.session_state["estado"]["situacion"] = "diagnosticar"
                response = requests.post(backend_url, json=st.session_state["estado"])
                response.raise_for_status()

                st.session_state["estado"] = response.json()

                #st.session_state["messages"].append({"role": "chatbot", "content": json.dumps(st.session_state["estado"], indent=4)}) #debug

        elif st.session_state["estado"]["situacion"] == "val_grup_simple" and st.session_state["estado"][
            "pregunta_actual"] is not None:
            #st.session_state["messages"].append({"role": "chatbot", "content": "validar pregunta grupo simple"})#debug
            user_input = st.session_state["user_message"]
            st.session_state["messages"].append({"role": "user", "content": user_input})
            st.session_state["user_message"] = ""  # Limpia el cuadro de texto

            # --- Validación de la respuesta ---
            prompt_validacion = f"""
                Eres un asistente médico.
                Tu tarea es determinar si la respuesta del usuario es un número válido entre 1 y {st.session_state["num_opciones_actual"] + 1} (inclusive),
                donde {st.session_state["num_opciones_actual"]+ 1} representa una respuesta negativa o la ausencia de síntomas.

                - Si la respuesta es un número válido dentro de este rango, o claquier forma de texto que haga referencia a una posicion(como "El primero" o "estpy de acuerdo con el segundo") ,responde ÚNICAMENTE con ese número.
                - Si la respuesta no es un número válido o no se entiende claramente como una de las opciones, responde con "REPETIR".

                Respuesta esperada (número o REPETIR):
                """
            prompt_usuario = user_input
            prompt = [
                SystemMessage(content=prompt_validacion),
                HumanMessage(content=prompt_usuario)
                ]

            resp_validacion = llm.invoke(prompt,config).content.lower().strip()
            seleccion=False

            if resp_validacion == "repetir":
                st.session_state["messages"].append({"role": "chatbot", "content": f"Disculpa, no he entendido tu respuesta. Por favor, asegúrate de responder con un número entre 1 y {st.session_state["num_opciones_actual"] + 1}."})
                st.session_state["esperando_respuesta"] = True

            elif resp_validacion.isdigit() and 1 <= int(resp_validacion) <= st.session_state["num_opciones_actual"]+ 1:
                respuesta_usuario_int = int(resp_validacion)
                seleccion = respuesta_usuario_int
            else:
                st.session_state["messages"].append({"role": "chatbot", "content": f"Respuesta inválida. Por favor, responde con un número entre 1 y {st.session_state["num_opciones_actual"]+ 1}."})
                st.session_state["esperando_respuesta"] = True

            # --- Procesamiento de la respuesta validada ---
            respuestas={}
            evidencia=[]
            if seleccion:
                for i, item in enumerate(st.session_state["estado"]['pregunta_actual']["items"]):
                    respuestas[item['id']]= "present" if respuesta_usuario_int == i + 1 else "absent"
                    evidencia.append({
                        'id': item['id'],
                        'choice_id': "present" if respuesta_usuario_int == i + 1 else "absent",
                        'source': 'suggest'
                        })
            else:
                for item in st.session_state["estado"]['pregunta_actual']["items"]:
                    respuestas[item['id']]= "absent"
                    evidencia.append({
                        'id': item['id'],
                        'choice_id': "absent",
                        'source': 'suggest'
                        })

            st.session_state["estado"]['evidencia'].extend(evidencia)
            st.session_state["estado"]["lista_preguntas"][st.session_state["estado"]['pregunta_actual']["text"]] = respuestas
            st.session_state["estado"]['pregunta_actual'] = None
            st.session_state["estado"]['evidencia'].extend(evidencia)
            st.session_state["estado"]["situacion"] = "diagnosticar"

            response = requests.post(backend_url, json=st.session_state["estado"])
            response.raise_for_status()
            st.session_state["estado"] = response.json()
            #st.session_state["messages"].append({"role": "chatbot", "content": st.session_state["estado"]}) debug





        elif st.session_state["estado"]["situacion"] == "hacer_minipreg" and st.session_state["estado"][
            "pregunta_actual"] is not None:


            user_input = st.session_state["user_message"]
            st.session_state["messages"].append({"role": "user", "content": user_input})
            st.session_state["user_message"] = ""
            st.session_state["esperando_respuesta"] = False

            st.session_state["estado"]["mensajes"].append(user_input)
            prompt_sistema = f"""
                Eres un asistente médico.Tu deber es asegurarte de que las respuestas de los usuarios se puedan clasificar como un sí, no o quizás de forma clara.
                En caso de que la respuesta no encaje de forma clara en una de estas 3 opciones responde REPETIR.
                En caso de que la respuesta sea claramente afirmativa responde con un SI.
                En caso de que la respuesta sea claramente negativa responde con un NO.
                Por último, si el usuario responde con un quizás claro responde QUIZAS
                                         """
            prompt = [
                SystemMessage(content=prompt_sistema),
                HumanMessage(content=user_input)
            ]
            respuesta = llm.invoke(prompt, config).content.lower().strip()

            situacion = ""
            if respuesta == "si":
                situacion = "present"
            elif respuesta == "no":
                situacion = "absent"
            elif respuesta == "quizas":
                situacion = "unknown"
            else:
                respuesta = "Disculpa, no he entendido tu respuesta. Por favor, responde con un sí, no o quizás."
                st.session_state["messages"].append({"role": "chatbot", "content": respuesta})
                st.session_state["esperando_respuesta"] = True

            if situacion in ["present", "absent", "unknown"]:
                st.session_state["evidencia"].append({
                    'id': list(st.session_state["mini_preg"][st.session_state["num_opciones_actual"]].values()),
                    'choice_id': situacion,
                    'source': 'suggest'
                })

            st.session_state["num_opciones_actual"] = st.session_state["num_opciones_actual"]+1
            st.session_state["esperando_respuesta"] = True

            if st.session_state["num_opciones_actual"] < len(st.session_state["mini_preg"]):

                st.session_state["messages"].append({"role": "chatbot", "content": list(st.session_state["mini_preg"][st.session_state["num_opciones_actual"]].keys())[0]})
                st.session_state["estado"]["situacion"] = "val_grup_simple"
                st.session_state["esperando_respuesta"] = True

            else:
                st.session_state["estado"]['evidencia'].extend(st.session_state["evidencia"])
                st.session_state["evidencia"]=[]
                st.session_state["estado"]['pregunta_actual'] = None
                st.session_state["estado"]["situacion"] = "diagnosticar"
                response = requests.post(backend_url, json=st.session_state["estado"])
                response.raise_for_status()

                st.session_state["estado"] = response.json()


        if st.session_state["estado"]["situacion"] == "diagnosticar" and st.session_state["estado"][
            "pregunta_actual"] is not None:
            if st.session_state["estado"]['pregunta_actual']['type'] == 'single':
                prompt_sistema = "Eres un traductor profesional que ayuda en consultas médicas. Traduce al español de la forma más directa posible, sin añadir texto de más."
                prompt_usuario = st.session_state["estado"]['pregunta_actual']["text"]
                pregunta = llm.invoke([SystemMessage(content=prompt_sistema), HumanMessage(content=prompt_usuario)],
                                    config).content
                pregunta_chatbot = pregunta + " *Responda con un sí, no o quizás.* "
                st.session_state["messages"].append({"role": "chatbot", "content": pregunta_chatbot})  # Add to messages
                st.session_state["estado"]["situacion"] = "val_preg_simple"
                st.session_state["esperando_respuesta"] = True  # Wait for user response

            elif st.session_state["estado"]['pregunta_actual']['type'] == 'group_single':
                #st.session_state["messages"].append({"role": "chatbot", "content": "pregunta grupo single"})#debug
                pregunta_ingles = st.session_state["estado"]['pregunta_actual']["text"]
                opciones_ingles = crear_pregunta(st.session_state["estado"]['pregunta_actual']["items"])
                st.session_state["num_opciones_actual"] = len(st.session_state["estado"]['pregunta_actual']["items"])

                # --- Primera llamada a Gemini: Traducción de la pregunta ---
                prompt_sistema = f"""
                                 Eres un traductor profesional para consultas médicas. Traduce la siguiente pregunta del inglés al español,
                                 asegurándote de que sea clara, concisa y adecuada para un paciente. No incluyas ninguna instrucción adicional
                                 ni hables como si estuvieras respondiendo al doctor. Formatea las opciones con un salto de línea entre ellas.
                                 """
                prompt_user = f"""
                                 Pregunta en inglés: "{pregunta_ingles}"
                                 Opciones en inglés (selecciona el número correspondiente): "{opciones_ingles}"
                                 """
                prompt_traduccion = [
                    SystemMessage(content=prompt_sistema),
                    HumanMessage(content=prompt_user)
                ]

                respuesta_traduccion = llm.invoke(prompt_traduccion, config).content
                pregunta_espanol = respuesta_traduccion
                st.session_state["messages"].append({"role": "chatbot", "content": pregunta_espanol})
                st.session_state["estado"]["situacion"] = "val_grup_simple"
                st.session_state["esperando_respuesta"] = True

            elif st.session_state["estado"]['pregunta_actual']['type'] == 'group_multiple':
                item_preg=st.session_state["estado"]["pregunta_actual"]["items"]
                context_preg=st.session_state["estado"]["pregunta_actual"]["text"]
                evidencia = []

                # --- Traducción del contexto de la pregunta ---
                prompt_contexto = [
                    SystemMessage(content="Eres un traductor profesional para consultas médicas. Traduce al español de la forma más directa posible, sin añadir texto de más."),
                    HumanMessage(content=context_preg)
                ]
                contexto_traducido = llm.invoke(prompt_contexto,config).content
                st.session_state["messages"].append({"role": "chatbot", "content": contexto_traducido})

                st.session_state["mini_preg"]=[]

                for x in item_preg:
                    pregunta_ingles = x["name"]

                    # --- Traducción del nombre de la pregunta, dado el contexto ---
                    prompt_pregunta = [
                        SystemMessage(content="Eres un traductor profesional para consultas médicas.Traduce al español de la forma más directa posible, sin añadir texto de más." \
                        "Se te va a proporcionar una pregunta simple y para poder traducurla necesitaras saber que antes se ha dado un el siguiente contexto: {contexto_traducido}" \
                        "ten encuenta este contexto para traducir la pregunta de forma correcta, pero no añadas nada que no estuviese en la pregunta original."),
                        HumanMessage(content=pregunta_ingles)
                    ]

                    pregunta_espanol = llm.invoke(prompt_pregunta,config).content
                    pregunta = pregunta_espanol+ "  *Responda con un sí, no o quizás.* "
                    st.session_state["mini_preg"].append({pregunta:x["id"]})

                st.session_state["estado"]["situacion"] = "hacer_minipreg"
                st.session_state["messages"].append({"role": "chatbot", "content": list(st.session_state["mini_preg"][0].keys())[0]})
                st.session_state["num_opciones_actual"] = 0
                st.session_state["evidencia"] = []
                st.session_state["esperando_respuesta"] = True

        if st.session_state["pedir_cita"] == True:

            user_input = st.session_state["user_message"]
            st.session_state["messages"].append({"role": "user", "content": user_input})
            st.session_state["user_message"] = ""
            st.session_state["esperando_respuesta"] = False

            st.session_state["estado"]["mensajes"].append(user_input)
            prompt_sistema = f"""
                Eres un asistente. Tu deber es asegurarte de que las respuestas de los usuarios se puedan clasificar como un sí o no de forma clara.
                En caso de que la respuesta no encaje de forma clara en una de estas 3 opciones responde REPETIR.
                En caso de que la respuesta sea claramente afirmativa responde con un SI.
                En caso de que la respuesta sea claramente negativa responde con un NO.
                                         """
            prompt = [
                SystemMessage(content=prompt_sistema),
                HumanMessage(content=user_input)
            ]
            respuesta = llm.invoke(prompt, config).content.lower().strip()

            if respuesta == "si":
                st.session_state["messages"].append({"role": "chatbot", "content":"Perfecto el Especialista ha sido avisado, pronto se pondra en contacto con usted"})
                st.session_state["estado"]["situacion"] = "reserva"
                response = requests.post(backend_url, json=st.session_state["estado"])
                response.raise_for_status()
                st.session_state["estado"] = response.json()

            elif respuesta == "no":
                st.session_state["messages"].append({"role": "chatbot", "content":"Ok, no pedire cita"})
                st.session_state["estado"]["situacion"] = "rag"

            else:
                respuesta = "Disculpa, no he entendido tu respuesta. Por favor, responde con un sí, no o quizás."
                st.session_state["messages"].append({"role": "chatbot", "content": respuesta})
                st.session_state["esperando_respuesta"] = True

        if st.session_state["estado"]["situacion"] =="rag":
            st.session_state["messages"].append({"role": "chatbot", "content":"Tenemos un especialista disponible que podria ayudarte con tu problema ¿Deseas solicitar cita para mañana a las 12AM?"})
            st.session_state["esperando_respuesta"] = True
            st.session_state["pedir_cita"] = True
        # Botón para enviar el mensaje
st.button("Enviar", on_click=send_user_message, disabled=not st.session_state["esperando_respuesta"])