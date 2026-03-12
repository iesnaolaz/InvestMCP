from app.services.stock_analyzer import analyze_stock

def find_opportunities():

    tickers = ["AAPL","MSFT","NVDA","AMD","TSLA","META"]

    results = []

    for ticker in tickers:

        data = analyze_stock(ticker)

        if data["score"] > 50:

            results.append(data)

    results.sort(key=lambda x: x["score"], reverse=True)

    return results