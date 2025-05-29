import numpy as np
import openai
import pandas as pd
from greenZonesMatrix import calcular_matriz_ahp_zonas_verdes
from publicServicesMatrix import calcular_matriz_ahp_servicios_publicos
from rentCostMatrix import calcular_matriz_ahp_coste_alquiler
from salesCostMatrix import calcular_matriz_ahp_coste_compra
from transportMatrix import calcular_matriz_ahp_transporte

def generar_pesos_criterios(
    c_tr,  # Costes vs Transporte
    c_sp,  # Costes vs Servicios Públicos
    c_zv,  # Costes vs Zonas Verdes
    tr_sp, # Transporte vs Servicios Públicos
    tr_zv, # Transporte vs Zonas Verdes
    sp_zv  # Servicios Públicos vs Zonas Verdes
):
    # Inicializar la matriz de comparación
    n = 4  # Número de criterios
    matriz = np.ones((n, n))
    
    # Asignar las comparaciones
    matriz[0, 1] = c_tr
    matriz[1, 0] = 1 / c_tr

    matriz[0, 2] = c_sp
    matriz[2, 0] = 1 / c_sp

    matriz[0, 3] = c_zv
    matriz[3, 0] = 1 / c_zv

    matriz[1, 2] = tr_sp
    matriz[2, 1] = 1 / tr_sp

    matriz[1, 3] = tr_zv
    matriz[3, 1] = 1 / tr_zv

    matriz[2, 3] = sp_zv
    matriz[3, 2] = 1 / sp_zv

    # Normalizar la matriz y calcular los pesos
    matriz_normalizada = matriz / matriz.sum(axis=0)
    pesos = matriz_normalizada.mean(axis=1)
    # Retornar los pesos
    return pesos

def calcular_barrio_ideal(
    modo_coste,  # "Compra" o "Alquiler"
    pesos_criterios  # Pesos calculados de los criterios
):
    """
    Calcula el barrio ideal según el método AHP.

    Args:
        modo_coste (str): Indica si se utiliza el criterio de "Compra" o "Alquiler" para los costes.
        pesos_criterios (list): Lista de pesos de los criterios en el orden [Coste, Transporte, Servicios Públicos, Ocio].

    Returns:
        pd.DataFrame: DataFrame ordenado con los barrios y sus puntuaciones finales.
    """
    # Obtener las matrices de los criterios
    if modo_coste == "Compra":
        matriz_costes = calcular_matriz_ahp_coste_compra()
    elif modo_coste == "Alquiler":
        matriz_costes = calcular_matriz_ahp_coste_alquiler()
    else:
        raise ValueError("El parámetro 'modo_coste' debe ser 'Compra' o 'Alquiler'.")

    matriz_transporte = calcular_matriz_ahp_transporte()
    matriz_servicios = calcular_matriz_ahp_servicios_publicos()
    matriz_zonas_verdes = calcular_matriz_ahp_zonas_verdes()

    # Combinar matrices con los pesos
    matrices = [
        matriz_costes["Peso"].values,
        matriz_transporte["Peso"].values,
        matriz_servicios["Peso"].values,
        matriz_zonas_verdes["Peso"].values
    ]

    # Ponderar las matrices y calcular puntuaciones finales
    puntuaciones_finales = sum(p * w for p, w in zip(matrices, pesos_criterios))

    # Crear un DataFrame con los resultados
    df_resultados = pd.DataFrame({
        "Distrito": matriz_zonas_verdes["Distrito"],  # Usamos los nombres de los barrios de cualquier matriz
        "Puntuación": puntuaciones_finales
    }).sort_values(by="Puntuación", ascending=False)
    top_3_barrios = df_resultados["Distrito"].head(3).tolist()
    df_top_3 = df_resultados.head(8).copy()
    df_top_3.insert(0, "Ranking", range(1, len(df_top_3) + 1))
    df_top_3 = df_top_3.reset_index(drop=True)

    # prompt = f"""
    # El distrito con mejor puntuación es: {top_3_barrios[0]}.
    # Describe detalladamente por qué es una zona ideal para vivir considerando los siguientes criterios:
    # - Coste
    # - Transporte
    # - Servicios Públicos
    # - Zonas Verdes

    # Cada criterio debe estar integrado en un párrafo cohesionado, evitando enumeraciones. Usa ejemplos reales del distrito para apoyar la descripción, pero no te extiendas más de 250 palabras en total. 
    # Evita repetir ideas y no concluyas con frases como "en resumen". Mantén la descripción directa y relevante.
    # """
    # openai.api_key =
    # response = openai.ChatCompletion.create(
    #         model="gpt-3.5-turbo",
    #         messages=[
    #             {"role": "system", "content": "Eres un experto en urbanismo y análisis de distritos."},
    #             {"role": "user", "content": prompt}
    #         ],
    #         max_tokens=400
    #     )    
    # texto = response["choices"][0]["message"]["content"]
   
    # Devolver el DataFrame ordenado
    return df_resultados, top_3_barrios, pesos_criterios, df_top_3#, texto

# print(calcular_barrio_ideal("Alquiler",generar_pesos_criterios(1,1,1,1,1,1)))
