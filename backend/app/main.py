from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.tools.search import search_stock
from pydantic import BaseModel
from app.services.stock_analyzer import analyze_stock
from app.services.opportunity_finder import find_opportunities

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

@app.post("/chat")
def chat(req: ChatRequest):

    query = req.query.upper()

    # detectar ticker simple
    tickers = ["AAPL","NVDA","AMD","MSFT","TSLA"]

    for ticker in tickers:

        if ticker in query:

            data = analyze_stock(ticker)

            return {
                "response": data
            }

    return {
        "response": "No he encontrado ticker en la pregunta"
    }