import yfinance as yf

def analyze_stock(ticker):

    stock = yf.Ticker(ticker)

    info = stock.info

    price = info.get("currentPrice")
    pe = info.get("trailingPE")
    growth = info.get("revenueGrowth")

    score = 0

    if pe and pe < 25:
        score += 40

    if growth and growth > 0.15:
        score += 40

    if price:
        score += 20

    return {
        "ticker": ticker,
        "price": price,
        "pe": pe,
        "growth": growth,
        "score": score
    }