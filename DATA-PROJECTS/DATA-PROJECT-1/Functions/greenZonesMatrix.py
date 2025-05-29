import numpy as np
import pandas as pd
from querys import obtener_zonas_verdes

def calcular_matriz_ahp_zonas_verdes():
    # Obtener los datos desde la consulta
    df = obtener_zonas_verdes()
    zonas_verdes = df["zonas_verdes"].values
    n = len(zonas_verdes)
    
    # Crear la matriz de comparación
    matriz_comparacion = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            matriz_comparacion[i, j] = zonas_verdes[i] / zonas_verdes[j]  # Directamente proporcional
    
    # Normalizar la matriz
    matriz_normalizada = matriz_comparacion / matriz_comparacion.sum(axis=0)
    
    # Calcular los pesos (promedio de filas normalizadas)
    pesos = matriz_normalizada.mean(axis=1)
    
    # Crear un DataFrame con los nombres de los barrios y sus pesos
    df_pesos = pd.DataFrame({"Distrito": df["distrito"], "Peso": pesos})
    
    return df_pesos