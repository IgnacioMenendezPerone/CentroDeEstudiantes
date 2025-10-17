from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import logging

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# Diccionario de respuestas expandido
RESPONSES = {
    r'hola|buenos días|saludos': 'Hola, soy SIVIA, ¿en qué puedo ayudarte?',
    r'quien eres|qué eres': 'Soy SIVIA, la asistente virtual de Manos Unidas. Estoy aquí para ayudarte con información sobre la organización.',
    r'manos unidas': 'Manos Unidas es una organización que trabaja para...',
    r'proyectos': 'Tenemos varios proyectos activos. Puedes verlos en la sección de Proyectos.',
    r'ayuda|ayudar': 'Puedes ayudar de varias formas: voluntariado, donaciones o difundiendo nuestra labor.',
    r'contacto|contactar': 'Puedes contactarnos a través de nuestro formulario en la web o por email.',
    r'ubicación|donde están': 'Nuestra sede principal está en...',
    r'donación|donar': 'Puedes hacer donaciones seguras a través de nuestra página web en la sección "Colabora".',
    r'voluntario|voluntariado': 'Para ser voluntario, necesitas...',
    r'gracias': '¡Gracias a ti! Estoy aquí para ayudarte.',
    r'adios|chau|hasta luego': '¡Hasta pronto! Si necesitas más ayuda, no dudes en volver.'
}

def get_response(prompt):
    try:
        logging.info(f"Recibida consulta: {prompt}")
        prompt = prompt.lower()
        for pattern, response in RESPONSES.items():
            if re.search(pattern, prompt):
                logging.info(f"Patrón coincidente encontrado: {pattern}")
                return response
        logging.warning(f"No se encontró respuesta para: {prompt}")
        return "Lo siento, no entiendo tu pregunta. ¿Podrías reformularla?"
    except Exception as e:
        logging.error(f"Error en get_response: {str(e)}")
        raise

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        if not prompt:
            return jsonify({"error": "El mensaje está vacío"}), 400
        
        reply = get_response(prompt)
        return jsonify({"reply": reply})
    
    except Exception as e:
        return jsonify({"error": "Error en el servidor"}), 500

if __name__ == '__main__':
    logging.info("Iniciando SIVIA...")
    app.run(debug=True, port=5000)
