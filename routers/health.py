"""
Care-On API — Health Check Router
POST /api/health/check — Main AI endpoint for the frontend.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from ai import full_health_check

router = APIRouter()


# ── Request / Response Models ──────────────────────────────────────────────────

class VitalsInput(BaseModel):
    bp_systolic: float = Field(..., description="Systolic blood pressure in mmHg", example=120)
    bp_diastolic: float = Field(..., description="Diastolic blood pressure in mmHg", example=80)
    sugar: float = Field(..., description="Blood sugar in mg/dL", example=100)
    heart_rate: float = Field(..., description="Heart rate in bpm", example=72)
    weight: Optional[float] = Field(None, description="Weight in kg", example=68)


class HistoryEntry(BaseModel):
    bp_systolic: Optional[float] = None
    bp_diastolic: Optional[float] = None
    sugar: Optional[float] = None
    heart_rate: Optional[float] = None


class HealthCheckRequest(BaseModel):
    vitals: VitalsInput
    history: list[HistoryEntry] = Field(default_factory=list)
    language: str = Field(default="english", description="Response language: english or urdu")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "vitals": {
                        "bp_systolic": 145,
                        "bp_diastolic": 92,
                        "sugar": 150,
                        "heart_rate": 85,
                        "weight": 70,
                    },
                    "history": [
                        {"bp_systolic": 125, "bp_diastolic": 82, "sugar": 105, "heart_rate": 72},
                        {"bp_systolic": 130, "bp_diastolic": 85, "sugar": 115, "heart_rate": 75},
                        {"bp_systolic": 138, "bp_diastolic": 88, "sugar": 128, "heart_rate": 78},
                        {"bp_systolic": 145, "bp_diastolic": 92, "sugar": 138, "heart_rate": 80},
                        {"bp_systolic": 152, "bp_diastolic": 95, "sugar": 145, "heart_rate": 82},
                    ],
                    "language": "english",
                }
            ]
        }
    }


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/health/check", summary="Full AI Health Check", tags=["AI Health"])
async def health_check(req: HealthCheckRequest):
    """
    Run the complete Care-On AI health analysis.

    - **Alert**: Rule-based vital sign evaluation (normal / warning / critical)
    - **Advice**: Gemini 2.5 Flash personalized health guidance
    - **Prediction**: 7-day risk forecast using linear regression on patient history

    The frontend calls this endpoint after the user submits their daily vitals.
    """
    vitals_dict = req.vitals.model_dump()
    history_dicts = [h.model_dump(exclude_none=True) for h in req.history]

    result = full_health_check(vitals_dict, history_dicts, req.language)
    return result
