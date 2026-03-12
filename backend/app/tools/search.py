import yfinance as yf

def search_stock(ticker):

    stock = yf.Ticker(ticker)

    info = stock.info

    return {
        "ticker": ticker,
        "price": info.get("currentPrice"),
        "pe": info.get("trailingPE"),
        "market_cap": info.get("marketCap")
    }