"""
Care-On AI — Gemini-Powered Health Advice Generator
Uses Gemini 2.5 Flash for warm, elderly-friendly health guidance.
Falls back to static advice if the API is unavailable.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Gemini client ──────────────────────────────────────────────────────────────
_client = None


def _get_client():
    """Lazy-init the Gemini client so import never crashes."""
    global _client
    if _client is None:
        import google.genai as genai
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


# ── Static fallback advice ─────────────────────────────────────────────────────

def _fallback_advice(vitals: dict) -> str:
    """Generate basic rule-based advice when Gemini is unavailable."""
    bp = vitals.get("bp_systolic", 0)
    sugar = vitals.get("sugar", 0)
    hr = vitals.get("heart_rate", 0)

    lines = []

    if bp >= 180 or sugar >= 250 or hr >= 130:
        lines.append("Your readings show some concerning values.")
        lines.append("Please contact your doctor as soon as possible.")
        lines.append("See doctor: Yes, urgently.")
    elif bp >= 140 or sugar >= 180 or hr >= 100:
        lines.append("Some of your readings are a bit elevated today.")
        lines.append("Try to rest, stay hydrated, and avoid salty or sugary foods.")
        lines.append("See doctor: Yes, within the next few days.")
    else:
        lines.append("Your readings look good today! Keep it up.")
        lines.append("Stay active with a gentle walk and drink plenty of water.")
        lines.append("See doctor: Not urgently, but keep your regular appointments.")

    return "\n".join(lines)


# ── Main advice function ───────────────────────────────────────────────────────

def get_ai_advice(vitals: dict, history: list, language: str = "english") -> str:
    """
    Generate personalized health advice using Gemini 2.5 Flash.

    Args:
        vitals:   Current vital readings (bp_systolic, bp_diastolic, sugar, heart_rate, weight)
        history:  List of past vital reading dicts (most recent entries)
        language: Response language — "english" (default)

    Returns:
        str: Warm, elderly-friendly health advice (max ~80 words)
    """
    # Build history context
    if history:
        history_str = "\n".join([
            f"  - BP {h.get('bp_systolic', '?')}/{h.get('bp_diastolic', '?')}, "
            f"Sugar {h.get('sugar', '?')}, HR {h.get('heart_rate', '?')}"
            for h in history[-5:]
        ])
    else:
        history_str = "  No previous readings available."

    lang_instruction = "simple, warm English"
    if language.lower() == "urdu":
        lang_instruction = "simple Urdu (اردو)"

    prompt = f"""You are a caring health assistant for elderly patients in the US/UK.
Respond in {lang_instruction}. Use very simple words. Be warm and reassuring.

Today's readings:
  - Blood Pressure: {vitals.get('bp_systolic', '?')}/{vitals.get('bp_diastolic', '?')} mmHg
  - Blood Sugar: {vitals.get('sugar', '?')} mg/dL
  - Heart Rate: {vitals.get('heart_rate', '?')} bpm
  - Weight: {vitals.get('weight', '?')} kg

Recent history:
{history_str}

Give exactly:
1) One sentence health assessment
2) One practical lifestyle tip
3) Should they see a doctor? Answer: Yes/No with brief reason

Keep it under 80 words. Be warm like a caring family member."""

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"⚠️  Gemini API error (falling back to static advice): {e}")
        return _fallback_advice(vitals)
