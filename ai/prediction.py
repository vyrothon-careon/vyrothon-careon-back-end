"""
Care-On AI — Health Risk Prediction Engine
Uses sklearn LinearRegression to forecast vital trends and compute risk scores.
"""

import numpy as np
from sklearn.linear_model import LinearRegression


def _forecast(values: list, days_ahead: int = 7) -> list:
    """
    Fit a linear regression on historical values and forecast N days ahead.

    Args:
        values:     List of float values (one per day)
        days_ahead: Number of days to forecast

    Returns:
        List of forecasted float values
    """
    X = np.arange(len(values)).reshape(-1, 1)
    y = np.array(values)
    model = LinearRegression().fit(X, y)

    future_X = np.arange(len(values), len(values) + days_ahead).reshape(-1, 1)
    return [round(float(v), 1) for v in model.predict(future_X)]


def _compute_risk_score(bp_forecast: list, sugar_forecast: list) -> tuple:
    """
    Compute a composite risk score (0-100) based on forecasted values.

    Scoring:
        BP forecast endpoint:    >160 → +40,  >140 → +20
        Sugar forecast endpoint: >200 → +40,  >140 → +20
        Rising BP trend:         +10
        Rising sugar trend:      +10

    Returns:
        (score: int, level: str)
    """
    score = 0

    # BP level component
    bp_end = bp_forecast[-1]
    if bp_end > 160:
        score += 40
    elif bp_end > 140:
        score += 20

    # Sugar level component
    sugar_end = sugar_forecast[-1]
    if sugar_end > 200:
        score += 40
    elif sugar_end > 140:
        score += 20

    # Trend component — is it rising?
    if bp_forecast[-1] > bp_forecast[0]:
        score += 10
    if sugar_forecast[-1] > sugar_forecast[0]:
        score += 10

    score = min(score, 100)

    # Map to risk level
    if score >= 60:
        level = "high"
    elif score >= 30:
        level = "moderate"
    else:
        level = "low"

    return score, level


def _get_prediction_text(bp_forecast: list, sugar_forecast: list, score: int, level: str) -> str:
    """
    Generate a warm prediction summary using Gemini, with static fallback.
    """
    prompt = (
        f"Patient 7-day forecast: BP systolic {bp_forecast}, Blood sugar {sugar_forecast}. "
        f"Risk score {score}/100 ({level}). "
        f"Write 2 warm, reassuring sentences for an elderly patient. "
        f"Suggest one specific preventive action. Max 50 words."
    )

    try:
        from ai.advice import _get_client
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"⚠️  Gemini prediction text error (using fallback): {e}")
        # Static fallback
        if level == "high":
            return (
                "Your health trend is showing some concerning patterns. "
                "Please schedule a doctor visit this week and try to reduce salt and sugar in your diet."
            )
        elif level == "moderate":
            return (
                "Your readings show a slight upward trend. Nothing to panic about, but let's keep an eye on it. "
                "Try a 15-minute walk each day and drink plenty of water."
            )
        else:
            return (
                "Your health trend looks stable and encouraging! "
                "Keep up your healthy habits and enjoy your day."
            )


def predict_health_risk(history: list) -> dict:
    """
    Predict 7-day health risk based on patient's vital reading history.

    Args:
        history: List of dicts with keys bp_systolic, bp_diastolic, sugar, heart_rate
                 Needs at least 5 readings to produce a prediction.

    Returns:
        dict with keys:
            - risk_score: int (0-100)
            - risk_level: "low" | "moderate" | "high"
            - forecast: {bp_systolic: [...], blood_sugar: [...]}
            - prediction: str (warm text summary)
        OR
            - status: "insufficient_data"
            - message: str
            - needed: int
    """
    if len(history) < 5:
        return {
            "status": "insufficient_data",
            "message": f"Need at least 5 daily readings for prediction. You have {len(history)}.",
            "needed": 5,
            "have": len(history),
        }

    # Extract values from history
    bp_values = [h.get("bp_systolic", 120) for h in history]
    sugar_values = [h.get("sugar", 100) for h in history]

    # Forecast 7 days ahead
    bp_forecast = _forecast(bp_values)
    sugar_forecast = _forecast(sugar_values)

    # Compute risk
    score, level = _compute_risk_score(bp_forecast, sugar_forecast)

    # Generate prediction text
    prediction_text = _get_prediction_text(bp_forecast, sugar_forecast, score, level)

    return {
        "risk_score": score,
        "risk_level": level,
        "forecast": {
            "bp_systolic": bp_forecast,
            "blood_sugar": sugar_forecast,
        },
        "prediction": prediction_text,
    }
