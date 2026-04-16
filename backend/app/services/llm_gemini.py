import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")


SYSTEM_PROMPT = (
    "Eres un asistente financiero. Responde en espanol de forma clara, "
    "breve y sin inventar datos factuales no verificados."
)

MODEL_NAME = "gemini-2.5-flash"


def _list_generate_models() -> list[str]:
    models = []
    for item in genai.list_models():
        methods = getattr(item, "supported_generation_methods", [])
        if "generateContent" in methods:
            name = getattr(item, "name", "")
            if name:
                models.append(name)
    return models


def ask_llm(prompt: str):
    """Returns (content, error_message)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, "GEMINI_API_KEY no definida"

    try:
        print("*Configurando Gemini con la API key...")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_NAME)
        print(f"*Enviando prompt a Gemini: {prompt}")
        response = model.generate_content(f"{SYSTEM_PROMPT}\n\nUsuario: {prompt}")
        print(f"*Respuesta cruda de Gemini: {response}")
        text = getattr(response, "text", None)
        if not text:
            return None, "Respuesta Gemini sin texto util"

        return text, None
    except Exception as exc:
        error_text = str(exc)
        if "not found" in error_text.lower() or "404" in error_text:
            try:
                available = _list_generate_models()
                short_list = ", ".join(available[:8]) if available else "ninguno"
                return (
                    None,
                    (
                        f"Modelo no disponible ({MODEL_NAME}). "
                        f"Modelos con generateContent para esta API key: {short_list}"
                    ),
                )
            except Exception as list_exc:
                return None, (
                    f"Error llamando a Gemini ({MODEL_NAME}): {exc}. "
                    f"No se pudo listar modelos disponibles: {list_exc}"
                )

        return None, f"Error llamando a Gemini ({MODEL_NAME}): {exc}"


   
