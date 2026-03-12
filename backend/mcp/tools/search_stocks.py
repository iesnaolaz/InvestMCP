import yfinance as yf
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()

@mcp.tool()
def analyze_stock(ticker: str):

    stock = yf.Ticker(ticker)
    info = stock.info

    return {
        "ticker": ticker,
        "price": info.get("currentPrice"),
        "pe": info.get("trailingPE"),
        "market_cap": info.get("marketCap"),
    }