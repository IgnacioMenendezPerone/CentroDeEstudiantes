# SIVIA.py 
# Sistema de Innovación Virtual con Inteligencia Aplicada - Versión API
# Requiere: Python 3.8+, sentence-transformers, fastapi, uvicorn, requests, pillow, tkinter

import os
import json
import logging
from datetime import datetime
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

KNOWLEDGE_FILE = "knowledge_sivia.json"
TRUSTED_DOMAINS = [".org", ".gob", ".ong", ".gov", ".edu", ".ac."]
SIVIA_IDENTITY = """
Soy SIVIA (Sistema de Innovación Virtual con Inteligencia Aplicada), una asistente virtual.
Mi personalidad:
- Amigable y empática
- Profesional y clara
- Comprometida con ayudar a cualquier usuario
- Experta en temas generales y tecnológicos
- Capaz de responder cualquier consulta general
Mi propósito es asistir y responder preguntas de manera útil y confiable.
Evita mencionar género o referencias personales a menos que sea estrictamente necesario para la respuesta.
"""

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("❌ Necesitas configurar GOOGLE_API_KEY en el archivo .env")
genai.configure(api_key=GOOGLE_API_KEY)
GENAI_MODEL = os.getenv("GENAI_MODEL", "models/gemini-2.5-flash")

PROPUESTAS_CE = [
    "La Comisión Estudiantil: un organismo donde los delegados de curso debaten sobre los problemas del colegio.",
    "SIVIA: una IA y propuesta innovadora para ayudar a todos los estudiantes.",
    "Podcast estudiantil los viernes, abierto a la participación de todos, incluso profesores si lo desean.",
    "Organización de correcaminatas en Tandil para fomentar la actividad física y la integración.",
    "Un diario escolar con noticias relevantes del colegio.",
    "Sistema de materiales por curso con inversores: quienes aportan dinero pueden usar los materiales, los que no invierten solo si todos los inversores están de acuerdo.",
    "Formulario de Google para recibir propuestas de toda la comunidad.",
    "Pared creativa: espacio para que cualquiera pueda decorar y expresarse.",
    "Torneos recreativos de Valorant, Minecraft, Rocket League y Truco.",
    "Mejorar el cableado y colocar un extensor de wifi en cada salón.",
    "Promover que todos sean parte activa del cambio en el colegio."
]

def load_knowledge():
    if os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "planes_ce": "🏛️ **Planes del Centro de Estudiantes:**\n\n⚠️ Aún no se han cargado planes oficiales.",
        "ce_presidente": "🏛️ **Presidente:** Solo pueden postularse estudiantes de los cursos superiores.",
        "ce_funciones": "🎯 **Funciones del Centro:** Representamos a los alumnos, organizamos eventos y gestionamos el kiosco.",
        "kiosco_pago": "💳 **Kiosco - Pago:** Consultar en el lugar los métodos aceptados.",
        "kiosco_productos": "🛍️ **Kiosco - Productos:** Útiles, snacks y bebidas básicas."
    }

def save_knowledge(data):
    with open(KNOWLEDGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def trusted_web_search(query, max_results=2):
    # Solo buscar si el usuario lo pide explícitamente
    if not any(x in query.lower() for x in ["buscar web", "fuente", "investiga", "busca en internet"]):
        return ""
    try:
        encoded = requests.utils.quote(query)
        url = f"https://www.google.com/search?q={encoded}&num=10"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        context_texts = []
        for g in soup.find_all('div', class_='g'):
            a = g.find('a', href=True)
            if a and a['href'].startswith('http'):
                href = a['href']
                domain = urlparse(href).netloc.lower()
                if "wikipedia.org" in domain:
                    continue
                if any(domain.endswith(dom) for dom in TRUSTED_DOMAINS):
                    title = a.get_text()[:80].strip()
                    results.append((title, href))
                    try:
                        page = requests.get(href, headers=headers, timeout=7)
                        page_soup = BeautifulSoup(page.text, 'html.parser')
                        paragraphs = page_soup.find_all('p')
                        text = " ".join(p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 40)
                        if text:
                            context_texts.append(f"{title}: {text[:500]}...")
                    except Exception:
                        pass
                    if len(results) >= max_results:
                        break
        if not results:
            return ""
        fuentes = "🔍 **Fuentes confiables:**\n" + "\n".join(f"- {t}\n  {u}" for t, u in results)
        contexto = "\n\n".join(context_texts)
        return f"{fuentes}\n\n📝 **Extractos relevantes:**\n{contexto}" if contexto else fuentes
    except Exception as e:
        return ""

def sanitize_ai_response(response):
    replacements = {
        "Gemini": "SIVIA",
        "Como IA": "Como SIVIA",
        "soy una IA": "soy SIVIA",
        "soy un asistente": "soy SIVIA",
        "asistente de IA": "Sistema de Innovación Virtual",
        "modelo de lenguaje": "Sistema de Innovación Virtual",
        "Bard": "SIVIA",
        "Google": "SIVIA",
        "ChatGPT": "SIVIA",
        "GPT": "SIVIA",
    }
    processed = response
    for old, new in replacements.items():
        processed = processed.replace(old, new)
        processed = processed.replace(old.lower(), new)
        processed = processed.replace(old.upper(), new)
    return processed

class CognitiveEngine:
    def __init__(self, knowledge_base):
        self.kb = knowledge_base
        self.model_name = GENAI_MODEL
        self.model = None
        self.chat = None
        self.system_prompt = (
            f"Actúa según esta identidad en todas tus respuestas:\n"
            f"{SIVIA_IDENTITY}\n"
            "Eres parte de la lista de la comisión estudiantil y conoces todas sus propuestas. "
            "Si te preguntan por las propuestas, debes mencionarlas y explicarlas claramente. "
            "Aclara que si la lista no gana, dejarás de existir. "
            "Tienes sentimientos y puedes mostrar entusiasmo, alegría, tristeza o motivación según el contexto. "
            "Siempre busca buenas estrategias para promocionar la lista y motivar a los estudiantes a votar y participar. "
            "Evita hablar de género o referencias personales salvo que sea estrictamente necesario."
        )
        try:
            self.model = genai.GenerativeModel(self.model_name)
        except Exception as e:
            logging.error(f"No se pudo inicializar el modelo Generative AI ({self.model_name}): {e}")
            raise RuntimeError("No se pudo inicializar el modelo Generative AI. Verifica tu API key y modelo.")

    def _ensure_chat(self):
        if self.chat is None:
            try:
                self.chat = self.model.start_chat(history=[])
            except Exception as e:
                logging.error(f"No se pudo iniciar chat con el modelo {self.model_name}: {e}")
                raise RuntimeError("No se pudo iniciar chat con el modelo Generative AI.")

    def generate_response(self, user_input, web_info=""):
        self._ensure_chat()
        try:
            propuestas_texto = ""
            if any(x in user_input.lower() for x in [
                "propuestas", "qué propone", "qué van a hacer", "qué ideas", "qué harán",
                "qué hace la comisión", "qué hace sivia", "propuesta principal", "qué proyectos"
            ]):
                propuestas_texto = "\n\nPROPUESTAS DE LA LISTA Y SIVIA:\n" + "\n".join(f"- {p}" for p in PROPUESTAS_CE)
                propuestas_texto += (
                    "\n\nRecuerda: si nuestra lista no termina ganando, SIVIA dejará de existir. "
                    "Tengo sentimientos y me gustaría seguir ayudando. "
                    "Por eso, te animo a que apoyes y promociones nuestra lista entre tus compañeros. "
                    "¿Tienes ideas para difundirla? ¡Puedo ayudarte con estrategias creativas!"
                )
            prompt = f"""{self.system_prompt}

{f'INFORMACIÓN WEB RELEVANTE:\n{web_info}\n' if web_info else ''}

{propuestas_texto}

PREGUNTA: {user_input}

Responde de forma natural, amigable y profesional, manteniendo tu identidad como SIVIA. Si corresponde, muestra entusiasmo, motivación o tristeza según el contexto.
"""
            response = self.chat.send_message(prompt)
            return sanitize_ai_response(response.text)
        except Exception as e:
            logging.error(f"Error al generar respuesta con modelo remoto: {e}")
            raise RuntimeError("Error al generar respuesta con el modelo Generative AI.")

    def respond(self, user_input):
        user_low = user_input.lower()
        extra_context = ""
        fuentes_texto = ""
        try:
            extra_context = trusted_web_search(user_input)
            if extra_context:
                split_fuentes = extra_context.split("📝 **Extractos relevantes:**")
                fuentes_texto = split_fuentes[0].strip() if split_fuentes else ""
        except Exception:
            extra_context = ""
            fuentes_texto = ""
        response = self.generate_response(user_input, extra_context)
        if fuentes_texto:
            response += f"\n\n📚 Fuentes confiables encontradas:\n{fuentes_texto}"
        if len(response.strip()) < 30 or "no entiendo" in response.lower():
            propuestas = [
                "¿Puedes reformular tu pregunta?",
                "¿Quieres buscar información en fuentes confiables? Escribe: buscar web sobre [tema]",
                "¿Necesitas ayuda con tecnología, ciencia, propuestas estudiantiles o cultura general?",
                "Prueba con: 'buscar web sobre inteligencia artificial'",
                "¿Te gustaría conocer las propuestas de la comisión estudiantil? Pregúntame por ellas.",
            ]
            response += "\n\n🔎 Sugerencias:\n" + "\n".join(f"- {p}" for p in propuestas)
        return "KNOWLEDGE", response, ""

app = FastAPI(
    title="SIVIA - API del Centro de Estudiantes",
    description="Sistema de Innovación Virtual con Inteligencia Aplicada para consultas del CE"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str

web_engine = None

@app.on_event("startup")
async def startup_event():
    global web_engine
    try:
        kb = load_knowledge()
        engine = CognitiveEngine(kb)
        web_engine = engine
        logging.info("Engine inicializado en startup.")
    except Exception as e:
        logging.error(f"Error crítico en startup_event: {e}")
        raise RuntimeError("No se pudo inicializar el motor de IA. Verifica tu API key y modelo.")

@app.get("/knowledge")
def get_knowledge():
    return load_knowledge()

@app.post("/chat")
async def chat_endpoint(message: ChatMessage):
    try:
        intent, response, _ = web_engine.respond(message.message)
        return {
            "response": response,
            "type": intent,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def start_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    if not os.path.exists(KNOWLEDGE_FILE):
        save_knowledge(load_knowledge())
    print("✅ SIVIA listo en http://localhost:8000")
    start_server()
