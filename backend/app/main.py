from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.tools.search import search_stock

app = FastAPI()

# Onartutako jatorriak (nire frontenda)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Gehitu middlewareak
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # onartutako jatorriak
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

from app.services.opportunity_finder import find_opportunities

@app.get("/opportunities")

def opportunities():

    return find_opportunities()