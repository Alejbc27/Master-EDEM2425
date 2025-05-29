import requests
from Estado import EstadoAgente

def reservar_cita(state: EstadoAgente) -> EstadoAgente:
    fecha ="9|2025-05-08T14:30:00"
    try:
        payload = {
            "patient": {"id": 201},
            "slot": {"slot_id": fecha},
        }
        response = requests.post("https://appointment-api-710866946885.europe-west1.run.app/appointments/", json=payload)
        print(response.status_code)
        print(response.json())
    except Exception as e:
        print(f"Error during appointment booking: {e}")
        
    return state
