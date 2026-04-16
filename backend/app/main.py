from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.tools.search import search_stock
from pydantic import BaseModel
from app.services.stock_analyzer import analyze_stock
from app.services.opportunity_finder import find_opportunities
from app.services.youtube_analyzer import analyze_youtube_video
from dotenv import load_dotenv
from pathlib import Path
from app.services.llm_gemini import ask_llm

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

app = FastAPI()

# Onartutako jatorriak (nire frontenda)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Gehitu middlewareak
app.add_middleware(
    CORSMiddleware,
    #allow_origins=origins,        # onartutako jatorriak
    allow_origins=["*"],  # permite cualquier origen (para desarrollo)
    allow_credentials=True,
    allow_methods=["*"],          # onartu GET, POST, etc.
    allow_headers=["*"],          # onartu headers
)

@app.get("/")
def home():
    return {"message": "Invest MCP martxan dago"}

@app.get("/stock/{ticker}")
def stock_data(ticker: str):
    return search_stock(ticker)

@app.get("/opportunities")

def opportunities():

    return find_opportunities()

#@app.post("/chat")

#def chat(query: str):

    # hona konektatuko da LLMa
#    return {"response": "processing query"}

class ChatRequest(BaseModel):
    query: str
    force_llm: bool = False


class YouTubeAnalysisRequest(BaseModel):
    url: str


@app.post("/youtube/analyze")
def analyze_youtube(req: YouTubeAnalysisRequest):
    data, error = analyze_youtube_video(req.url)
    if error:
        return {
            "ok": False,
            "error": error,
            "video_url": req.url,
        }

    return {
        "ok": True,
        "video_url": req.url,
        "result": data,
    }

@app.post("/chat")
def chat(req: ChatRequest):
    print(f"Jasotako querya: {req.query}, force_llm: {req.force_llm}")  
    if req.force_llm:
        print("**Force LLM enabled, skipping ticker detection.")
        llm_response, llm_error = ask_llm(req.query)
        if llm_response:
            return {
                "response": llm_response
            }
        return {
            "response": f"No se pudo usar LLM: {llm_error}"
        }
    print(f"Jasotako querya: {req.query}")
    query = req.query.upper()

    # detectar ticker simple
    tickers = ["AAPL","NVDA","AMD","MSFT","TSLA"]

    for ticker in tickers:

        if ticker in query:

            data = analyze_stock(ticker)

            return {
                "response": data
            }

    llm_response, llm_error = ask_llm(req.query)
    print(f"LLM response: {llm_response}")
    if llm_response:
        return {
            "response": llm_response
        }

    return {
        "response": f"No he encontrado ticker y el LLM fallo: {llm_error}"
    }