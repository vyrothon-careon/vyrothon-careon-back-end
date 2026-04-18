"""
Care-On AI — Health Risk Prediction Engine (v2)

Features:
    - Weighted linear regression (recent readings matter more)
    - Z-score outlier detection (typos / device errors filtered)
    - Confidence intervals on all forecasts (honest uncertainty)
    - R² goodness-of-fit check (warns when trend is unreliable)
    - 4-vital risk scoring: BP systolic, diastolic, sugar, heart rate
    - Smooth scoring functions (no cliff effects)
    - Physiological clamping (no impossible forecast values)
    - Gemini timeout with static fallback
"""

import logging
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────────────────────

# Hard physiological bounds — forecasts are clamped to these ranges
VITAL_BOUNDS = {
    "bp_systolic": (60, 300),
    "bp_diastolic": (30, 200),
    "sugar": (20, 600),
    "heart_rate": (20, 250),
}

MIN_READINGS = 5           # Minimum data points required per vital
GEMINI_TIMEOUT = 10        # Seconds to wait for Gemini before falling back
OUTLIER_Z_THRESHOLD = 2.5  # Z-score cutoff for outlier removal


# ── Outlier Detection ─────────────────────────────────────────────────────────

def _remove_outliers(values: list, z_threshold: float = OUTLIER_Z_THRESHOLD) -> tuple:
    """
    Remove values more than z_threshold standard deviations from the mean.

    Args:
        values:      List of float readings
        z_threshold: Number of standard deviations for cutoff

    Returns:
        (cleaned_values: list, num_removed: int)
    """
    if len(values) < 3:
        return values, 0

    arr = np.array(values, dtype=float)
    mean, std = np.mean(arr), np.std(arr)

    if std == 0:
        return values, 0  # All identical — no outliers possible

    z_scores = np.abs((arr - mean) / std)
    cleaned = arr[z_scores < z_threshold].tolist()

    # If too many removed, keep original to avoid data loss
    if len(cleaned) < MIN_READINGS:
        return values, 0

    return cleaned, len(values) - len(cleaned)


# ── Weighted Forecast with Confidence Intervals ──────────────────────────────

def _forecast(values: list, days_ahead: int = 7, vital_type: str = "bp_systolic") -> dict:
    """
    Fit a weighted linear regression and forecast N days ahead.

    Recent readings get exponentially higher weight so the model
    prioritizes the patient's current trajectory over old history.

    Args:
        values:     List of float values (one per day, cleaned)
        days_ahead: Number of days to forecast
        vital_type: Key in VITAL_BOUNDS for clamping

    Returns:
        {
            "predictions": [{day, predicted, lower_bound, upper_bound, confidence}, ...],
            "r_squared":   float,
            "slope":       float (change per day),
        }
    """
    X = np.arange(len(values)).reshape(-1, 1)
    y = np.array(values, dtype=float)

    # Exponential weights — recent readings matter more
    weights = np.exp(np.linspace(0, 2, len(values)))

    model = LinearRegression().fit(X, y, sample_weight=weights)

    # Goodness of fit
    y_pred_train = model.predict(X)
    r2 = max(0.0, float(r2_score(y, y_pred_train)))

    # Residual standard error for confidence intervals
    residuals = y - y_pred_train
    std_error = float(np.std(residuals)) if len(residuals) > 1 else 0.0

    # Forecast future values
    future_X = np.arange(len(values), len(values) + days_ahead).reshape(-1, 1)
    raw_predictions = model.predict(future_X)

    # Physiological clamping bounds
    lo, hi = VITAL_BOUNDS.get(vital_type, (0, 999))

    predictions = []
    for i, pred in enumerate(raw_predictions):
        # Uncertainty grows with forecast distance
        distance_factor = 1 + (i / len(values))
        margin = 1.96 * std_error * distance_factor  # ~95% CI
        confidence = round(max(0.1, 1 - (i * 0.08)), 2)

        clamped = float(np.clip(pred, lo, hi))
        lower = float(np.clip(pred - margin, lo, hi))
        upper = float(np.clip(pred + margin, lo, hi))

        predictions.append({
            "day": i + 1,
            "predicted": round(clamped, 1),
            "lower_bound": round(lower, 1),
            "upper_bound": round(upper, 1),
            "confidence": confidence,
        })

    return {
        "predictions": predictions,
        "r_squared": round(r2, 3),
        "slope": round(float(model.coef_[0]), 2),
    }


# ── Smooth Scoring Functions (no cliff effects) ──────────────────────────────

def _bp_sys_risk(value: float) -> int:
    """Smooth 0→25: 0 at ≤120, 25 at ≥180."""
    if value <= 120:
        return 0
    if value >= 180:
        return 25
    return round(25 * (value - 120) / 60)


def _sugar_risk(value: float) -> int:
    """Smooth 0→25: 0 at ≤100, 25 at ≥250."""
    if value <= 100:
        return 0
    if value >= 250:
        return 25
    return round(25 * (value - 100) / 150)


def _hr_risk(value: float) -> int:
    """Smooth 0→20: penalizes both high (>90) and low (<60) heart rate."""
    if 60 <= value <= 90:
        return 0
    if value > 90:
        if value >= 140:
            return 20
        return round(20 * (value - 90) / 50)
    else:
        if value <= 30:
            return 20
        return round(20 * (60 - value) / 30)


def _bp_dia_risk(value: float) -> int:
    """Smooth 0→15: 0 at ≤80, 15 at ≥120."""
    if value <= 80:
        return 0
    if value >= 120:
        return 15
    return round(15 * (value - 80) / 40)


# ── Composite Risk Score ──────────────────────────────────────────────────────

def _compute_risk_score(forecasts: dict) -> tuple:
    """
    Compute a composite risk score (0-100) from all available vital forecasts.

    Scoring breakdown (max 100):
        BP Systolic endpoint:   0-25  (smooth ramp)
        Blood Sugar endpoint:   0-25  (smooth ramp)
        Heart Rate endpoint:    0-20  (smooth, both high & low)
        BP Diastolic endpoint:  0-15  (smooth ramp)
        Rising/changing trends: 0-15  (up to ~4 pts per vital)

    Returns:
        (score: int, level: str)
    """
    score = 0

    # BP Systolic
    if "bp_systolic" in forecasts:
        preds = forecasts["bp_systolic"]["predictions"]
        score += _bp_sys_risk(preds[-1]["predicted"])
        if preds[-1]["predicted"] > preds[0]["predicted"]:
            score += 4

    # Blood Sugar
    if "sugar" in forecasts:
        preds = forecasts["sugar"]["predictions"]
        score += _sugar_risk(preds[-1]["predicted"])
        if preds[-1]["predicted"] > preds[0]["predicted"]:
            score += 4

    # Heart Rate
    if "heart_rate" in forecasts:
        preds = forecasts["heart_rate"]["predictions"]
        score += _hr_risk(preds[-1]["predicted"])
        if abs(preds[-1]["predicted"] - preds[0]["predicted"]) > 10:
            score += 4  # Rapid change in either direction is concerning

    # BP Diastolic
    if "bp_diastolic" in forecasts:
        preds = forecasts["bp_diastolic"]["predictions"]
        score += _bp_dia_risk(preds[-1]["predicted"])
        if preds[-1]["predicted"] > preds[0]["predicted"]:
            score += 3

    score = min(score, 100)

    if score >= 60:
        level = "high"
    elif score >= 30:
        level = "moderate"
    else:
        level = "low"

    return score, level


# ── Confidence Assessment ─────────────────────────────────────────────────────

def _determine_confidence(forecasts: dict) -> str:
    """Overall prediction confidence based on average R² across all vitals."""
    r2_values = [data["r_squared"] for data in forecasts.values()]
    avg_r2 = float(np.mean(r2_values))

    if avg_r2 >= 0.7:
        return "high"
    elif avg_r2 >= 0.4:
        return "moderate"
    else:
        return "low"


# ── Prediction Text (Gemini + fallback) ───────────────────────────────────────

def _fallback_text(level: str) -> str:
    """Static fallback prediction text when Gemini is unavailable."""
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


def _get_prediction_text(forecasts: dict, score: int, level: str) -> str:
    """Generate a warm prediction summary using Gemini, with static fallback."""
    # Build forecast summary for the prompt
    parts = []
    for vital, data in forecasts.items():
        preds = data["predictions"]
        parts.append(f"{vital}: {preds[0]['predicted']} → {preds[-1]['predicted']}")

    prompt = (
        f"Patient 7-day forecast: {', '.join(parts)}. "
        f"Risk score {score}/100 ({level}). "
        f"Write 2 warm, reassuring sentences for an elderly patient. "
        f"Suggest one specific preventive action. Max 50 words."
    )

    try:
        from ai.advice import _get_client
        client = _get_client()

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
            )
            response = future.result(timeout=GEMINI_TIMEOUT)

        return response.text

    except FuturesTimeoutError:
        logger.warning("Gemini prediction text timed out after %ds, using fallback", GEMINI_TIMEOUT)
        return _fallback_text(level)
    except Exception as e:
        logger.warning("Gemini prediction text error, using fallback: %s", e)
        return _fallback_text(level)


# ── Main Prediction Function ─────────────────────────────────────────────────

def predict_health_risk(history: list) -> dict:
    """
    Predict 7-day health risk from patient vital reading history.

    Pipeline:
        1. Extract each vital's readings (skip missing — no fake imputation)
        2. Remove outliers via z-score filtering
        3. Fit weighted linear regression (recent readings prioritized)
        4. Forecast 7 days with confidence intervals
        5. Clamp to physiological bounds
        6. Compute smooth composite risk score across all available vitals
        7. Assess prediction confidence via R²
        8. Generate warm summary text via Gemini (with timeout + fallback)

    Args:
        history: List of dicts with keys bp_systolic, bp_diastolic, sugar, heart_rate.
                 Needs at least 5 readings per vital to forecast that vital.

    Returns:
        dict with risk_score, risk_level, confidence, forecast, prediction, data_quality
        OR dict with status="insufficient_data" if not enough readings
    """
    if len(history) < MIN_READINGS:
        return {
            "status": "insufficient_data",
            "message": f"Need at least {MIN_READINGS} daily readings for prediction. You have {len(history)}.",
            "needed": MIN_READINGS,
            "have": len(history),
        }

    # ── Extract, clean, and forecast each vital ──
    vital_keys = ["bp_systolic", "bp_diastolic", "sugar", "heart_rate"]
    forecasts = {}
    total_readings = 0
    total_outliers = 0

    for vital in vital_keys:
        # Only use history entries that actually recorded this vital (no fake defaults)
        raw_values = [h[vital] for h in history if vital in h]

        if len(raw_values) < MIN_READINGS:
            continue  # Not enough data for this vital — skip it

        # Remove outliers
        cleaned, removed = _remove_outliers(raw_values)
        total_outliers += removed
        total_readings += len(cleaned)

        # Forecast with weighted regression + confidence intervals + clamping
        forecasts[vital] = _forecast(cleaned, days_ahead=7, vital_type=vital)

    # ── Guard: need at least BP or sugar for a meaningful prediction ──
    if not forecasts:
        return {
            "status": "insufficient_data",
            "message": "Not enough complete readings for any vital sign. Need at least 5 per vital.",
            "needed": MIN_READINGS,
        }

    if "bp_systolic" not in forecasts and "sugar" not in forecasts:
        return {
            "status": "insufficient_data",
            "message": "Need at least 5 blood pressure or blood sugar readings for risk prediction.",
            "available_vitals": list(forecasts.keys()),
        }

    # ── Compute risk score from all available forecasts ──
    score, level = _compute_risk_score(forecasts)

    # ── Assess overall confidence ──
    confidence = _determine_confidence(forecasts)

    # ── Generate prediction text ──
    prediction_text = _get_prediction_text(forecasts, score, level)

    # ── Build response ──
    forecast_output = {}
    for vital, data in forecasts.items():
        slope = data["slope"]
        if slope > 0.5:
            trend = "rising"
        elif slope < -0.5:
            trend = "falling"
        else:
            trend = "stable"

        forecast_output[vital] = {
            "values": data["predictions"],
            "r_squared": data["r_squared"],
            "trend": trend,
            "slope_per_day": slope,
        }

    return {
        "risk_score": score,
        "risk_level": level,
        "confidence": confidence,
        "forecast": forecast_output,
        "prediction": prediction_text,
        "data_quality": {
            "readings_used": total_readings,
            "outliers_removed": total_outliers,
            "vitals_analyzed": list(forecasts.keys()),
        },
    }
