"""
Stock analyzer con indicadores técnicos de momento de compra.

Indicadores calculados
----------------------
MA20 / MA50   Moving Average de 20 y 50 sesiones.
              Señal alcista: precio > MA20 > MA50.

RSI           Relative Strength Index (14 sesiones).
              <30 → sobrevendido (compra potencial).
              30–70 → neutral.
              >70 → sobrecomprado.

Volumen       Comparación volumen actual vs media 20 sesiones.
              Subida de precio + volumen alto confirma la compra.

MACD          Diferencia EMA12 – EMA26 y línea señal EMA9.
              Cruce alcista MACD > señal → impulso comprador.

Soporte       Mínimo de las últimas 20 sesiones.
Resistencia   Máximo de las últimas 20 sesiones.

ATR           Average True Range (14 sesiones).
              Mide volatilidad; valores altos indican mayor riesgo.

Scorer / Semáforo
-----------------
Cada indicador suma puntos al score (0-100):
  +20  Tendencia alcista (precio > MA20 > MA50)
  +15  RSI en zona favorable (<50 y >20 — no sobrecomprado)
  +15  Volumen confirma movimiento (vol actual > 1.2× media)
  +20  MACD alcista (macd_line > signal_line y > 0)
  +15  Precio cerca de soporte (<5 % sobre mínimo 20 sesiones)
  +15  Fundamentales aceptables (PE < 25 y growth > 0)

Semáforo:
  🟢 COMPRA    score >= 60
  🟡 NEUTRAL   score 35–59
  🔴 EVITAR    score < 35
"""

import yfinance as yf
import pandas as pd


# ---------------------------------------------------------------------------
# Helpers técnicos
# ---------------------------------------------------------------------------

def _rsi(closes: pd.Series, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi_series = 100 - (100 / (1 + rs))
    val = rsi_series.iloc[-1]
    return round(float(val), 2) if not pd.isna(val) else None


def _macd(closes: pd.Series) -> dict:
    if len(closes) < 27:
        return {"macd_line": None, "signal_line": None, "histogram": None}
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd_line": round(float(macd_line.iloc[-1]), 4),
        "signal_line": round(float(signal_line.iloc[-1]), 4),
        "histogram": round(float(histogram.iloc[-1]), 4),
    }


def _atr(hist: pd.DataFrame, period: int = 14) -> float | None:
    if len(hist) < period + 1:
        return None
    high = hist["High"]
    low = hist["Low"]
    prev_close = hist["Close"].shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr_val = tr.rolling(period).mean().iloc[-1]
    return round(float(atr_val), 4) if not pd.isna(atr_val) else None


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

def _calculate_score_and_signal(
    price: float | None,
    ma20: float | None,
    ma50: float | None,
    rsi: float | None,
    vol_current: float | None,
    vol_avg20: float | None,
    macd_line: float | None,
    signal_line: float | None,
    support: float | None,
    pe: float | None,
    growth: float | None,
) -> tuple[int, str, dict]:
    """
    Devuelve (score 0-100, semaforo, detalle_señales).

    Reglas de puntuación
    --------------------
    Tendencia alcista   +20  precio > MA20 > MA50
    RSI favorable       +15  20 < RSI < 50 (sobrevendido o neutral-bajo, no sobrecomprado)
    Volumen confirma    +15  vol_actual > 1.2 × vol_media_20
    MACD alcista        +20  macd_line > signal_line y macd_line > 0
    Cerca de soporte    +15  precio < soporte * 1.05
    Fundamentales ok    +15  PE < 25 y growth > 0
    """
    score = 0
    signals: dict[str, bool | None] = {}

    # Tendencia
    if price is not None and ma20 is not None and ma50 is not None:
        trend_ok = price > ma20 > ma50
        signals["trend_bullish"] = trend_ok
        if trend_ok:
            score += 20
    else:
        signals["trend_bullish"] = None

    # RSI
    if rsi is not None:
        rsi_ok = 20 < rsi < 50
        signals["rsi_favorable"] = rsi_ok
        if rsi_ok:
            score += 15
    else:
        signals["rsi_favorable"] = None

    # Volumen
    if vol_current is not None and vol_avg20 and vol_avg20 > 0:
        vol_ok = vol_current > vol_avg20 * 1.2
        signals["volume_confirms"] = vol_ok
        if vol_ok:
            score += 15
    else:
        signals["volume_confirms"] = None

    # MACD
    if macd_line is not None and signal_line is not None:
        macd_ok = macd_line > signal_line and macd_line > 0
        signals["macd_bullish"] = macd_ok
        if macd_ok:
            score += 20
    else:
        signals["macd_bullish"] = None

    # Soporte
    if price is not None and support is not None and support > 0:
        near_support = price < support * 1.05
        signals["near_support"] = near_support
        if near_support:
            score += 15
    else:
        signals["near_support"] = None

    # Fundamentales
    if pe is not None and growth is not None:
        fund_ok = pe < 25 and growth > 0
        signals["fundamentals_ok"] = fund_ok
        if fund_ok:
            score += 15
    else:
        signals["fundamentals_ok"] = None

    # Semáforo
    if score >= 60:
        semaphore = "🟢 COMPRA"
    elif score >= 35:
        semaphore = "🟡 NEUTRAL"
    else:
        semaphore = "🔴 EVITAR"

    return score, semaphore, signals


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def analyze_stock(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    info = stock.info

    price = info.get("currentPrice")
    pe = info.get("trailingPE")
    growth = info.get("revenueGrowth")

    # Histórico: 3 meses para MA50, MACD, ATR
    hist = stock.history(period="3mo")

    ma20 = ma50 = rsi_val = vol_avg20 = vol_current = support = resistance = atr_val = None
    macd_data: dict = {"macd_line": None, "signal_line": None, "histogram": None}

    if not hist.empty and "Close" in hist.columns:
        closes = hist["Close"].dropna()

        if len(closes) >= 20:
            ma20 = round(float(closes.rolling(20).mean().iloc[-1]), 4)
            vol_avg20 = float(hist["Volume"].rolling(20).mean().iloc[-1]) if "Volume" in hist else None

        if len(closes) >= 50:
            ma50 = round(float(closes.rolling(50).mean().iloc[-1]), 4)

        rsi_val = _rsi(closes)
        macd_data = _macd(closes)
        atr_val = _atr(hist)

        if len(closes) >= 20:
            support = round(float(hist["Low"].tail(20).min()), 4)
            resistance = round(float(hist["High"].tail(20).max()), 4)

        if "Volume" in hist.columns and not hist["Volume"].empty:
            vol_current = float(hist["Volume"].iloc[-1])

    score, semaphore, signals = _calculate_score_and_signal(
        price=price,
        ma20=ma20,
        ma50=ma50,
        rsi=rsi_val,
        vol_current=vol_current,
        vol_avg20=vol_avg20,
        macd_line=macd_data["macd_line"],
        signal_line=macd_data["signal_line"],
        support=support,
        pe=pe,
        growth=growth,
    )

    return {
        "ticker": ticker,
        # Precio y fundamentales
        "price": price,
        "pe": pe,
        "growth": growth,
        # Medias móviles
        "ma20": ma20,
        "ma50": ma50,
        # RSI
        "rsi": rsi_val,
        # Volumen
        "volume_current": vol_current,
        "volume_avg20": round(vol_avg20, 0) if vol_avg20 else None,
        # MACD
        "macd_line": macd_data["macd_line"],
        "signal_line": macd_data["signal_line"],
        "macd_histogram": macd_data["histogram"],
        # Soporte / Resistencia / ATR
        "support": support,
        "resistance": resistance,
        "atr": atr_val,
        # Scorer
        "score": score,
        "semaphore": semaphore,
        "signals": signals,
    }
