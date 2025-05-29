from flask import Flask, request, jsonify
from typing import List, Dict, Optional, TypedDict
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import datetime
import os


client = firestore.Client(project="data-project-3-457210")
coleccion = client.collection("patients-db-dp3")

app = Flask(__name__)

@app.route('/guardar_estado', methods=['POST'])
def guardar_estado():
    try:
        estado = request.json

        if not estado or not isinstance(estado, dict):
            return jsonify({"error": "Estado inválido"}), 400

        doc_id = str(uuid.uuid4())
        
        coleccion.document(doc_id).set(estado)

        return jsonify({
            "success": True,
            "message": "Estado guardado correctamente",
            "id": doc_id
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Error al guardar el estado: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
