import streamlit as st
import pydeck as pdk
import pandas as pd
from createTop3Polygons import extraer_top3_poligonos_sql
from calcular_ahp import generar_pesos_criterios
from calcular_ahp import calcular_barrio_ideal
from createPolygons import extraer_poligonos_sql

# Configuración de la página
st.set_page_config(page_title="District Serch", layout="wide", initial_sidebar_state="expanded")

# Estilos globales y personalizados
# Estilos globales y personalizados
st.markdown(
    """
    <style>
    /* Fondo de la página */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
        background-color: #1c1c1c;
        color: white;
        font-family: 'Comic Sans';
    }
    
    /* Título principal */
    h1 {
        font-size: 2rem;
        color: #4CAF50;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
        margin-bottom: 20px;
        text-align: center;
    }

    /* Contenedor centrado */
    .center-container {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        margin-top: 20px;
    }

    /* Subtítulos */
    h2, h3 {
        color: #ffffff;
        font-weight: 600;
        margin-bottom: 15px;
    }

    /* Personalización de la barra lateral */
    [data-testid="stSidebar"] {
        background-color: #1c1c1c;
        border-right: 2px solid #4CAF50;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.3);
        padding-top: 20px;
    }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] label {
        color: #4CAF50;
        font-weight: bold;
    }

    /* Botón personalizado */
    .stButton>button {
        display: block;
        margin: 20px auto;
        padding: 15px 25px;
        background: linear-gradient(90deg, #32a852, #3dc973);
        color: white;
        font-size: 18px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
        border: none;
        border-radius: 12px;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1), 0px 1px 3px rgba(0, 0, 0, 0.06);
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #3dc973, #32a852);
        transform: translateY(-2px);
        color: #ffffff;
        box-shadow: 0px 10px 15px rgba(0, 0, 0, 0.2), 0px 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:active {
        transform: translateY(0);
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1), 0px 1px 3px rgba(0, 0, 0, 0.06);
    }

    /* Selectbox personalizado */
    div[data-baseweb="select"] {
        border-radius: 8px !important;
        border: 1px solid #4CAF50 !important;
        background: #4CAF50 !important;
        color: #4CAF50 !important;
        font-size: 16px !important;
        font-weight: bold !important;
        padding: 2px !important;
    }

    /* Radio button personalizado */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 16px;
        font-weight: bold;
        color: #4CAF50;
        cursor: pointer;
        padding: 5px 10px;
        border-radius: 5px;
        transition: all 0.3s ease;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: rgba(76, 175, 80, 0.1);
        color: #32a852;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {
        accent-color: #4CAF50;
        width: 18px;
        height: 18px;
        cursor: pointer;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Título principal
st.markdown(
    """
    <h1 style="
        font-size: 3rem;
        font-family: 'Poppins', sans-serif;
        text-transform: uppercase;
        color: #4CAF50;
        margin-bottom: 30px;
        text-align: center;
        letter-spacing: 1.5px;
    ">
        ¿Cuál es tu distrito ideal?
    </h1>
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600&display=swap');
    </style>
    """,
    unsafe_allow_html=True,
)

# Barra lateral
opcion = st.sidebar.radio("¿Qué tipo de vivienda buscas?", ["Alquiler", "Compra"])

# Lógica según la selección
if opcion == "Alquiler":
    tipo_vivienda = opcion
elif opcion == "Compra":
    tipo_vivienda = opcion

with st.sidebar:
    st.subheader("Selecciona la importancia relativa entre los criterios en comparación por pares:")
    st.markdown("""
    - **1:** Ambos criterios tienen igual importancia.
    - **Mayor que 1:** El criterio a la izquierda es más importante que el de la derecha.
    - **Menor que 1 (por ejemplo, 1/3):** El criterio a la derecha es más importante que el de la izquierda.
    """)
    c_tr = st.slider("Costes vs Transporte", min_value=1/5, max_value=5.0, value=1.0, key="c_tr")
    c_sp = st.slider("Costes vs Servicios Públicos", min_value=1/5, max_value=5.0, value=1.0, key="c_sp")
    c_zv = st.slider("Costes vs Zonas Verdes", min_value=1/5, max_value=5.0, value=1.0, key="c_zv")
    tr_sp = st.slider("Transporte vs Servicios Públicos", min_value=1/5, max_value=5.0, value=1.0, key="tr_sp")
    tr_zv = st.slider("Transporte vs Zonas Verdes", min_value=1/5, max_value=5.0, value=1.0, key="tr_zv")
    sp_zv = st.slider("Servicios Públicos vs Zonas Verdes", min_value=1/5, max_value=5.0, value=1.0, key="sp_zv")


# Botón funcional
calcular_btn = st.sidebar.button("Obten tu lugar ideal")

# Mapa centrado en Valencia con tamaño ajustado
st.markdown('<div class="center-container">', unsafe_allow_html=True)
map_data = pd.DataFrame({
    'lat': [39.4699],
    'lon': [-0.3763]
})
polygons = extraer_poligonos_sql()

# Formatear los datos para Pydeck
geojson_features = []
for polygon in polygons:
    geojson_features.append({
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [polygon]  # Encapsular en otra lista
        },
        "properties": {}
    })

geojson_data = {
    "type": "FeatureCollection",
    "features": geojson_features
}

# Crear la capa para Pydeck
layer = pdk.Layer(
    "GeoJsonLayer",
    geojson_data,
    pickable=True,
    stroked=True,
    filled=True,
    lineWidthScale=20,
    lineWidthMinPixels=1,
    get_line_color=[0, 160, 0],
    get_fill_color=[76, 175, 80,50],
)


# Acción del botón
if calcular_btn:
    pesos_criterios = generar_pesos_criterios(c_tr,c_sp,c_zv,tr_sp,tr_zv,sp_zv)
    barrio_ideal = calcular_barrio_ideal(tipo_vivienda,pesos_criterios)
    polygons = extraer_top3_poligonos_sql(barrio_ideal[1])

geojson_features = []
for polygon in polygons:
    geojson_features.append({
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [polygon]  # Encapsular en otra lista
        },
        "properties": {}
    })

geojson_data = {
    "type": "FeatureCollection",
    "features": geojson_features
}

# Crear la capa para Pydeck
layer = pdk.Layer(
    "GeoJsonLayer",
    geojson_data,
    pickable=True,
    stroked=True,
    filled=True,
    lineWidthScale=20,
    lineWidthMinPixels=1,
    get_line_color=[0, 160, 0],
    get_fill_color=[76, 175, 80,50],
)
# Crear el mapa con PyDeck
st.pydeck_chart(pdk.Deck(
    map_style='mapbox://styles/mapbox/light-v9',
    initial_view_state=pdk.ViewState(
        latitude=39.4659,
        longitude=-0.3763,
        zoom=12,
        pitch=0,
    ),
    layers=[layer],
), width=1200, height=600, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

if calcular_btn:
    top_barrios = barrio_ideal[3]
    top_3_barrios = top_barrios["Distrito"].head(3).tolist()
    col1, col2 = st.columns([1, 2])  # Ajusta el ancho relativo de las columnas
    
    with col1:
        st.dataframe(top_barrios, width=400)
    
    # with col2:
    #     # Generar el texto con ChatGPT API
    #     texto_generado =barrio_ideal[4]
    #     st.markdown(f"""
    #     <div style="color: #4CAF50; font-size: 18px; font-family: 'Poppins', sans-serif; margin-left: 20px;">
    #         {texto_generado}
    #     </div>
    #     """, unsafe_allow_html=True)