import numpy as np
import pandas as pd
from querys import obtener_transporte

def calcular_matriz_ahp_transporte():
    df = obtener_transporte()
    total_transporte = df["total_transporte"].values
    n = len(total_transporte)
    
    # Crear la matriz de comparación
    matriz_comparacion = np.zeros((n, n))

    
    for i in range(n):
        for j in range(n):
            matriz_comparacion[i, j] = total_transporte[i] / total_transporte[j]
    
    # Normalizar la matriz
    matriz_normalizada = matriz_comparacion / matriz_comparacion.sum(axis=0)
    
    # Calcular los pesos (promedio de filas normalizadas)
    pesos = matriz_normalizada.mean(axis=1)
    
    # Crear un DataFrame con los nombres de los barrios y sus pesos
    df_pesos = pd.DataFrame({"Distrito": df["distrito"], "Peso": pesos})
    
    return df_pesos