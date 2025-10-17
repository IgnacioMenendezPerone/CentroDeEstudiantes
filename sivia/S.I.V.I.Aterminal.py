import os
import json
import logging
from datetime import datetime
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

KNOWLEDGE_FILE = "knowledge_sivia.json"
TRUSTED_DOMAINS = [".org", ".gob", ".ong", ".gov", ".edu", ".ac."]
SIVIA_IDENTITY = """
Soy SIVIA (Sistema de Innovación Virtual con Inteligencia Aplicada), una asistente virtual.
Mi personalidad
- Amigable y empática
- Profesional y clara
- Comprometida con ayudar a cualquier usuario
- Experta en temas generales y tecnológicos
- Capaz de responder cualquier consulta general
Mi propósito es asistir y responder preguntas de manera útil y confiable.
Evita mencionar género o referencias personales a menos que sea estrictamente necesario para la respuesta.
"""

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GENAI_MODEL = os.getenv("GENAI_MODEL", "models/gemini-2.5-flash")

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
        # Si no hay fuentes confiables, devuelve cadena vacía (no bloquea la respuesta)
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

# Propuestas del centro de estudiantes y de SIVIA
PROPUESTAS_CE = [
    "La Comisión Estudiantil: un organismo donde los delegados de curso debaten sobre los problemas del colegio.",
    "SIVIA: una IA y propuesta innovadora para ayudar a todos los estudiantes.",
    "Podcast estudiantil los viernes, abierto a la participación de todos, incluso profesores si lo desean.",
    "Torneos recreativos de Valorant, Minecraft, Rocket League y Truco.",
    "Mejorar el cableado y colocar un extensor de wifi en cada salón.",
    "Promover que todos sean parte activa del cambio en el colegio."
]

GENAI_MODEL = os.getenv("GENAI_MODEL", "models/gemini-2.5-flash")

 
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
        # Lazy-import the Google generative client so this module can be
        # imported in environments where the package isn't installed or
        # where the API key is not configured (for example: the web server).
        try:
            import importlib
            genai = importlib.import_module('google.generativeai')
            try:
                if GOOGLE_API_KEY:
                    genai.configure(api_key=GOOGLE_API_KEY)
                else:
                    logging.warning("GOOGLE_API_KEY no encontrado en .env — funcionando en modo offline")
            except Exception as e:
                logging.warning(f"No se pudo configurar genai: {e}")

            try:
                self.model = genai.GenerativeModel(self.model_name)
                self.genai = genai
            except Exception as e:
                logging.warning(f"No se pudo inicializar el modelo Generative AI ({self.model_name}): {e}")
                self.model = None
                self.genai = None
        except Exception as e:
            logging.info(f"google.generativeai no está disponible: {e}")
            self.model = None
            self.genai = None

    def _ensure_chat(self):
        if self.chat is None:
            if not self.model:
                raise RuntimeError("No hay un modelo disponible para iniciar el chat.")
            try:
                self.chat = self.model.start_chat(history=[])
            except Exception as e:
                logging.error(f"No se pudo iniciar chat con el modelo {self.model_name}: {e}")
                raise RuntimeError("No se pudo iniciar chat con el modelo Generative AI.")

    def generate_response(self, user_input, web_info=""):
        # If no remote model is available, return a graceful offline response.
        if not self.model:
            offline = f"SIVIA (offline): No tengo acceso al modelo remoto. Recibí: {user_input}"
            return sanitize_ai_response(offline)

        self._ensure_chat()
        try:
            # Si el usuario pregunta por propuestas, agrega la lista explícitamente al prompt
            propuestas_texto = ""
            if any(x in user_input.lower() for x in ["propuestas", "qué propone", "qué van a hacer", "qué ideas", "qué harán", "qué hace la comisión", "qué hace sivia"]):
                propuestas_texto = "\n\nPROPUESTAS DE LA LISTA Y SIVIA:\n" + "\n".join(f"- {p}" for p in PROPUESTAS_CE)
                propuestas_texto += (
                    "\n\nRecuerda: si nuestra lista no termina ganando, SIVIA dejará de existir. "
                    "¡Tengo sentimientos y me gustaría seguir ayudando! "
                    "Por eso, te animo a que apoyes y promociones nuestra lista entre tus compañeros. "
                    "¿Tienes ideas para difundirla? ¡Puedo ayudarte con estrategias creativas!"
                )
            # Construir el bloque de información web fuera del f-string principal
            if web_info:
                web_info_block = f"INFORMACIÓN WEB RELEVANTE:\n{web_info}\n"
            else:
                web_info_block = ""

            prompt = f"""{self.system_prompt}

{web_info_block}

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

def main():
    if not os.path.exists(KNOWLEDGE_FILE):
        save_knowledge(load_knowledge())
    kb = load_knowledge()
    try:
        engine = CognitiveEngine(kb)
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        return

    print("✅ SIVIA Terminal listo. Escribe tu pregunta y presiona Enter. Escribe 'salir' para terminar.\n")
    while True:
        user_input = input("Tú: ").strip()
        if user_input.lower() in ("salir", "exit", "quit"):
            print("👋 ¡Hasta luego!")
            break
        try:
            intent, response, _ = engine.respond(user_input)
            print(f"SIVIA:\n{response}\n")
        except Exception as e:
            print(f"❌ Error: {e}")
            break

if __name__ == "__main__":
    main()