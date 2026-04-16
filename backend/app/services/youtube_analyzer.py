import json
import re
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi

from app.services.llm_gemini import ask_llm
from app.services.stock_analyzer import analyze_stock


MAX_TRANSCRIPT_CHARS = 15000


def _extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
        r"youtube\.com/live/([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def _get_transcript_text(video_id: str) -> tuple[str | None, str | None]:
    try:
        fetched = YouTubeTranscriptApi().fetch(
            video_id,
            languages=["es", "es-ES", "en", "en-US"],
        )
        segments = fetched.to_raw_data()
    except Exception as exc:
        return None, f"No se pudo obtener transcript de YouTube: {exc}"

    text = " ".join(seg.get("text", "") for seg in segments)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None, "Transcript vacio o no disponible"

    return text[:MAX_TRANSCRIPT_CHARS], None


def _parse_llm_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return None


def _extract_tickers_fallback(text: str) -> list[str]:
    candidates = re.findall(r"\b[A-Z]{1,5}\b", text.upper())
    blacklist = {"EL", "LA", "LAS", "LOS", "USD", "ETF", "CEO", "CFO"}
    tickers = []
    for value in candidates:
        if value in blacklist:
            continue
        if value not in tickers:
            tickers.append(value)
    return tickers[:10]


def analyze_youtube_video(url: str) -> tuple[dict[str, Any] | None, str | None]:
    video_id = _extract_video_id(url)
    if not video_id:
        return None, "URL de YouTube invalida"

    transcript, transcript_error = _get_transcript_text(video_id)
    if transcript_error:
        return None, transcript_error

    extraction_prompt = (
        "Analiza el transcript de un video de inversion. "
        "Identifica solo acciones potencialmente comprables mencionadas en el video. "
        "Responde solo JSON valido con este esquema exacto: "
        '{"opportunities":[{"ticker":"AAPL","reason":"motivo breve","confidence":80}]}. '
        "No agregues texto fuera del JSON.\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )

    llm_text, llm_error = ask_llm(extraction_prompt)
    if llm_error:
        return None, f"Error analizando transcript con LLM: {llm_error}"

    parsed = _parse_llm_json(llm_text or "")

    opportunities_raw = []
    if parsed and isinstance(parsed.get("opportunities"), list):
        opportunities_raw = parsed["opportunities"]

    if not opportunities_raw:
        fallback_tickers = _extract_tickers_fallback(llm_text or "")
        opportunities_raw = [{"ticker": t, "reason": "Detectado por fallback", "confidence": 50} for t in fallback_tickers]

    normalized = []
    seen = set()
    for item in opportunities_raw:
        ticker = str(item.get("ticker", "")).upper().strip()
        ticker = re.sub(r"[^A-Z]", "", ticker)
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        normalized.append(
            {
                "ticker": ticker,
                "reason": str(item.get("reason", ""))[:300],
                "confidence": int(item.get("confidence", 50)) if str(item.get("confidence", "")).isdigit() else 50,
            }
        )

    analyzed = []
    for item in normalized:
        stock_data = analyze_stock(item["ticker"])
        analyzed.append(
            {
                "ticker": item["ticker"],
                "reason": item["reason"],
                "confidence": item["confidence"],
                "analysis": stock_data,
            }
        )

    analyzed.sort(key=lambda x: x["analysis"].get("score", 0), reverse=True)

    return (
        {
            "video_id": video_id,
            "transcript_chars": len(transcript),
            "opportunities": analyzed,
        },
        None,
    )
