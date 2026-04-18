"""
Care-On AI — Health Check Orchestrator
Wires together alerts, advice, and prediction into a single response.
"""

from ai.alerts import check_alert
from ai.advice import get_ai_advice
from ai.prediction import predict_health_risk


def full_health_check(vitals: dict, history: list, language: str = "english") -> dict:
    """
    Run the complete AI health analysis pipeline.

    Args:
        vitals:   Current vital readings dict
        history:  List of past vital reading dicts
        language: "english" (default) or "urdu"

    Returns:
        {
            "vitals":     dict  — echo of input vitals,
            "alert":      dict  — {level, alerts[]},
            "advice":     str   — Gemini-generated health advice,
            "prediction": dict  — {risk_score, risk_level, forecast, prediction} or insufficient_data,
        }
    """
    return {
        "vitals": vitals,
        "alert": check_alert(vitals),
        "advice": get_ai_advice(vitals, history, language),
        "prediction": predict_health_risk(history),
    }
