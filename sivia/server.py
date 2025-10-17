from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    logging.error('GOOGLE_API_KEY no encontrado en .env')


# Serve static files from this directory (so Flask can serve sivia.html and assets)
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Simple in-memory session store: {session_id: [messages...]}
SESSIONS = {}
SESSION_COOKIE = 'sivia_sid'
MAX_HISTORY = 10

# Try to reuse the full CognitiveEngine from the terminal app so the web API
# exposes the same features (propuestas, knowledge base, web search, etc.).
engine = None
try:
    # Load the module from file because its filename contains dots and is not
    # a valid import identifier. This avoids import resolution problems.
    import importlib.util
    module_path = os.path.join(os.path.dirname(__file__), 'S.I.V.I.Aterminal.py')
    spec = importlib.util.spec_from_file_location('sivia_terminal', module_path)
    sivia_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sivia_mod)
    try:
        kb = sivia_mod.load_knowledge()
        engine = sivia_mod.CognitiveEngine(kb)
        logging.info('CognitiveEngine cargado y listo')
    except Exception as e:
        logging.warning(f'No se pudo inicializar CognitiveEngine: {e}')
        engine = None
except Exception as e:
    logging.info(f'No se pudo cargar S.I.V.I.Aterminal: {e}')
    engine = None


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({'error': 'prompt vacío'}), 400
    # Get or create session id from cookie
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        import uuid
        sid = str(uuid.uuid4())
        SESSIONS[sid] = []
    if sid not in SESSIONS:
        SESSIONS[sid] = []
    # Append user prompt to session history
    SESSIONS[sid].append({'author': 'user', 'text': prompt, 'ts': str(__import__('datetime').datetime.utcnow())})
    # Keep history bounded
    if len(SESSIONS[sid]) > MAX_HISTORY:
        SESSIONS[sid] = SESSIONS[sid][-MAX_HISTORY:]
    # Intent: proxy to generative model if available, otherwise simple echo
    try:
        if engine:
            # Provide recent session history as context if engine supports it
            history_text = "\n".join(f"{m['author']}: {m['text']}" for m in SESSIONS[sid][-MAX_HISTORY:])
            intent, reply, _ = engine.respond(prompt)
            # Append assistant reply to history
            SESSIONS[sid].append({'author': 'assistant', 'text': reply, 'ts': str(__import__('datetime').datetime.utcnow())})
            resp = jsonify({'reply': reply})
            resp.set_cookie(SESSION_COOKIE, sid, httponly=True)
            return resp
        # Fallback: try to import google.generativeai lazily and call it
        try:
            import importlib
            genai = importlib.import_module('google.generativeai')
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(os.getenv('GENAI_MODEL', 'models/gemini-2.5-flash'))
            chat = model.start_chat(history=[])
            response = chat.send_message(f"{prompt}")
            text = response.text
        except Exception:
            # Offline fallback; store reply in session history
            text = f"SIVIA (offline): No tengo acceso al modelo, recibí: {prompt}"
        SESSIONS[sid].append({'author': 'assistant', 'text': text, 'ts': str(__import__('datetime').datetime.utcnow())})
        resp = jsonify({'reply': text})
        resp.set_cookie(SESSION_COOKIE, sid, httponly=True)
        return resp
    except Exception as e:
        logging.error(f'Error al generar respuesta: {e}')
        return jsonify({'error': 'Error al generar respuesta'}), 500



@app.route('/')
def index():
    # Serve the chat page
    return app.send_static_file('sivia.html')



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)
