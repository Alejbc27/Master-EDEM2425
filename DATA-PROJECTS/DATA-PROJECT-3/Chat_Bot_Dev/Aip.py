from flask import Flask, request, jsonify
from agente_por_nodos import grafo

app = Flask(__name__)

@app.route("/modificar_estado/", methods=["POST"])
def modificar_estado():
    try:
        estado_recibido = request.json
        for output in grafo.stream(estado_recibido):
            for key, value in output.items():
                estado_recibido = value
        return jsonify(estado_recibido), 200

    except Exception as e:
        return jsonify({"error": f"Ocurrió un error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)