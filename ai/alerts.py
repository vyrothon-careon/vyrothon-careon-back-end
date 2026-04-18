"""
Care-On AI — Rule-Based Vital Sign Alert Engine
Thresholds calibrated to AHA (US) / NICE (UK) clinical guidelines.
"""


def check_alert(vitals: dict) -> dict:
    """
    Evaluate vitals against clinical thresholds and return alert level + messages.

    Args:
        vitals: dict with keys bp_systolic, bp_diastolic, sugar, heart_rate, weight

    Returns:
        {"level": "normal" | "warning" | "critical", "alerts": [str, ...]}
    """
    alerts = []
    level = "normal"

    def _escalate(new_level: str):
        nonlocal level
        priority = {"normal": 0, "warning": 1, "critical": 2}
        if priority.get(new_level, 0) > priority.get(level, 0):
            level = new_level

    # ── Blood Pressure — Systolic ──────────────────────────────────────────
    bp_sys = vitals.get("bp_systolic", 0)
    if bp_sys >= 180:
        alerts.append("CRITICAL: Blood pressure dangerously high (systolic ≥180). Call your doctor NOW.")
        _escalate("critical")
    elif bp_sys >= 140:
        alerts.append("WARNING: Blood pressure is elevated (systolic ≥140). Please rest and monitor.")
        _escalate("warning")
    elif bp_sys > 0 and bp_sys < 90:
        alerts.append("WARNING: Blood pressure is low (systolic <90). Sit down and drink water.")
        _escalate("warning")

    # ── Blood Pressure — Diastolic ─────────────────────────────────────────
    bp_dia = vitals.get("bp_diastolic", 0)
    if bp_dia >= 120:
        alerts.append("CRITICAL: Diastolic pressure dangerously high (≥120). Seek immediate help.")
        _escalate("critical")
    elif bp_dia >= 90:
        alerts.append("WARNING: Diastolic pressure elevated (≥90). Rest and monitor.")
        _escalate("warning")

    # ── Blood Sugar ────────────────────────────────────────────────────────
    sugar = vitals.get("sugar", 0)
    if sugar > 0:
        if sugar >= 250:
            alerts.append("CRITICAL: Blood sugar very high (≥250 mg/dL). Seek help immediately.")
            _escalate("critical")
        elif sugar >= 180:
            alerts.append("WARNING: Blood sugar is high (≥180 mg/dL). Avoid sugary food and monitor.")
            _escalate("warning")
        elif sugar <= 54:
            alerts.append("CRITICAL: Blood sugar dangerously low (≤54 mg/dL). Eat something sweet NOW.")
            _escalate("critical")
        elif sugar <= 70:
            alerts.append("WARNING: Blood sugar is low (≤70 mg/dL). Please eat something now.")
            _escalate("warning")

    # ── Heart Rate ─────────────────────────────────────────────────────────
    hr = vitals.get("heart_rate", 0)
    if hr > 0:
        if hr >= 130:
            alerts.append("CRITICAL: Heart rate very high (≥130 bpm). Sit down and call your doctor.")
            _escalate("critical")
        elif hr >= 100:
            alerts.append("WARNING: Heart rate is elevated (≥100 bpm). Rest and breathe slowly.")
            _escalate("warning")
        elif hr <= 40:
            alerts.append("CRITICAL: Heart rate dangerously low (≤40 bpm). Call emergency services.")
            _escalate("critical")
        elif hr <= 50:
            alerts.append("WARNING: Heart rate is low (≤50 bpm). Sit down and monitor.")
            _escalate("warning")

    # ── Normal case ────────────────────────────────────────────────────────
    if level == "normal":
        alerts.append("All vitals are within normal range. Keep up the good work!")

    return {"level": level, "alerts": alerts}
