"""
Care-On AI — Health Check Orchestrator
Wires together alerts, advice, and prediction into a single response.
Runs advice + prediction in parallel to halve response time.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

from ai.alerts import check_alert
from ai.advice import get_ai_advice
from ai.prediction import predict_health_risk

logger = logging.getLogger(__name__)


def full_health_check(vitals: dict, history: list, language: str = "english") -> dict:
    """
    Run the complete AI health analysis pipeline.

    - Alerts run synchronously (instant, rule-based, no external calls)
    - Advice + Prediction run in parallel via ThreadPoolExecutor

    Args:
        vitals:   Current vital readings dict
        history:  List of past vital reading dicts
        language: "english" (default) or "urdu"

    Returns:
        {
            "vitals":     dict  — echo of input vitals,
            "alert":      dict  — {level, alerts[]},
            "advice":     str   — Gemini-generated health advice,
            "prediction": dict  — risk score, forecasts, confidence, etc.,
        }
    """
    t_start = time.time()

    # ── Alerts — rule-based, instant, no external calls ──
    try:
        alert = check_alert(vitals)
    except Exception as e:
        logger.error("Alert engine failed: %s", e, exc_info=True)
        alert = {"level": "unknown", "alerts": [f"Alert check unavailable: {e}"]}

    t_alerts = time.time()

    # ── Advice + Prediction — run in parallel (both call Gemini independently) ──
    with ThreadPoolExecutor(max_workers=2) as pool:
        advice_future = pool.submit(get_ai_advice, vitals, history, language)
        prediction_future = pool.submit(predict_health_risk, history)

        try:
            advice = advice_future.result(timeout=30)
        except Exception as e:
            logger.error("Advice generation failed: %s", e, exc_info=True)
            advice = "Health advice temporarily unavailable."

        try:
            prediction = prediction_future.result(timeout=30)
        except Exception as e:
            logger.error("Prediction engine failed: %s", e, exc_info=True)
            prediction = {"status": "error", "message": f"Prediction unavailable: {e}"}

    t_end = time.time()

    logger.info(
        "Health check complete — alerts: %.3fs, advice+prediction: %.3fs, total: %.3fs",
        t_alerts - t_start,
        t_end - t_alerts,
        t_end - t_start,
    )

    return {
        "vitals": vitals,
        "alert": alert,
        "advice": advice,
        "prediction": prediction,
    }
