from flask import Flask, jsonify
from flask_cors import CORS

print("Iniciando configuración de Flask...")

app = Flask(__name__)
CORS(app)

@app.route('/test', methods=['POST'])
def test_endpoint():
    return jsonify({'status': 'success'})

print("Rutas registradas:")
print(app.url_map)

if __name__ == "__main__":
    app.run(debug=True, port=5000) 