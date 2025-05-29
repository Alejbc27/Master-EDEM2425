import numpy as np
import pandas as pd
from querys import obtener_hospitales, obtener_escuelas

def calcular_matriz_ahp_servicios_publicos():
    # Obtener datos de hospitales y escuelas
    df_hospitales = obtener_hospitales()
    df_escuelas = obtener_escuelas()
    
    # Combinar ambas tablas en una única DataFrame sumando los valores
    df_combined = pd.merge(df_hospitales, df_escuelas, on="distrito")
    df_combined["total_servicios_publicos"] = df_combined["total_hospitales"] + df_combined["total_centros_educativos"]
    
    total_servicios = df_combined["total_servicios_publicos"].values
    n = len(total_servicios)
    
    # Crear la matriz de comparación
    matriz_comparacion = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            matriz_comparacion[i, j] = total_servicios[i] / total_servicios[j]  # Directamente proporcional
    
    # Normalizar la matriz
    matriz_normalizada = matriz_comparacion / matriz_comparacion.sum(axis=0)
    
    # Calcular los pesos (promedio de filas normalizadas)
    pesos = matriz_normalizada.mean(axis=1)
    
    # Crear un DataFrame con los nombres de los barrios y sus pesos
    df_pesos = pd.DataFrame({"Distrito": df_combined["distrito"], "Peso": pesos})
    
    return df_pesos
