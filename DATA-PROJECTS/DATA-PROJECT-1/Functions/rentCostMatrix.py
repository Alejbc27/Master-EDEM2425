import numpy as np
import pandas as pd
from querys import obtener_coste_alquiler

def calcular_matriz_ahp_coste_alquiler():
    # Obtener los datos desde la consulta
    df = obtener_coste_alquiler()
    precios = df["precio_medio_2022_m2"].values
    n = len(precios)
    
    # Crear la matriz de comparación
    matriz_comparacion = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            matriz_comparacion[i, j] = precios[j] / precios[i]
    
    # Normalizar la matriz
    matriz_normalizada = matriz_comparacion / matriz_comparacion.sum(axis=0)
    
    # Calcular los pesos (promedio de filas normalizadas)
    pesos = matriz_normalizada.mean(axis=1)
    
    # Crear un DataFrame con los nombres de los barrios y sus pesos
    df_pesos = pd.DataFrame({"Distrito": df["nombre_distrito"], "Peso": pesos})
    
    return df_pesos
