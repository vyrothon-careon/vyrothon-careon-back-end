# ─────────────────────────────────────────────
# AI ROUTER — DROP ZAKARIA'S LOGIC BELOW HERE
# Do not modify the router prefix or file name
# ─────────────────────────────────────────────

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import asc
from datetime import datetime, timedelta

from database import get_db
import models
from ai import full_health_check

router = APIRouter()


# ── Request / Response Models ──────────────────────────────────────────────────

class VitalsInput(BaseModel):
    bp_systolic: float = Field(..., ge=1, le=400, description="Systolic blood pressure in mmHg", example=120)
    bp_diastolic: float = Field(..., ge=1, le=300, description="Diastolic blood pressure in mmHg", example=80)
    sugar: float = Field(..., ge=1, le=1000, description="Blood sugar in mg/dL", example=100)
    heart_rate: float = Field(..., ge=1, le=300, description="Heart rate in bpm", example=72)
    weight: Optional[float] = Field(None, ge=1, le=500, description="Weight in kg", example=68)


class HistoryEntry(BaseModel):
    bp_systolic: Optional[float] = Field(None, ge=1, le=400)
    bp_diastolic: Optional[float] = Field(None, ge=1, le=300)
    sugar: Optional[float] = Field(None, ge=1, le=1000)
    heart_rate: Optional[float] = Field(None, ge=1, le=300)


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


class UserHealthCheckRequest(BaseModel):
    vitals: VitalsInput
    language: str = Field(default="english", description="Response language: english or urdu")


# ── Endpoint 1: Standalone (manual history) ────────────────────────────────────

@router.post("/health/check", summary="AI Health Check (manual history)", tags=["AI Health"])
def health_check(req: HealthCheckRequest):
    """
    Run the complete Care-On AI health analysis with manually provided history.

    - **Alert**: Rule-based vital sign evaluation (normal / warning / critical)
    - **Advice**: Gemini 2.5 Flash personalized health guidance
    - **Prediction**: 7-day risk forecast using weighted linear regression

    The frontend sends both current vitals AND past readings in the request body.

    Uses a synchronous def (not async) so FastAPI runs it in a threadpool,
    preventing the blocking Gemini API calls from freezing the event loop.
    """
    vitals_dict = req.vitals.model_dump()
    history_dicts = [h.model_dump(exclude_none=True) for h in req.history]

    result = full_health_check(vitals_dict, history_dicts, req.language)
    return result


# ── Endpoint 2: DB-integrated (auto-pulls user history) ───────────────────────

@router.post("/health/user-check", summary="AI Health Check (DB history)", tags=["AI Health"])
async def user_health_check(
    req: UserHealthCheckRequest,
    user_id: int = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Run AI health analysis using the user's stored vitals history from the database.

    Pipeline:
        1. Verify the user exists
        2. Save the new vital reading to the database
        3. Pull the user's last 30 days of readings as history
        4. Run the full AI pipeline (alerts + advice + prediction)
        5. Return the combined result

    This is the primary endpoint the frontend should call after a user logs their vitals.
    The user_id is passed as a query parameter, and only current vitals are in the body.
    """
    # ── Verify user exists ──
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ── Save new vitals to DB ──
    vitals_dict = req.vitals.model_dump()
    new_vital = models.UserVitalReading(
        user_id=user_id,
        bp_systolic=vitals_dict["bp_systolic"],
        bp_diastolic=vitals_dict["bp_diastolic"],
        sugar=vitals_dict["sugar"],
        heart_rate=vitals_dict["heart_rate"],
        weight=vitals_dict.get("weight"),
    )
    db.add(new_vital)
    await db.commit()

    # ── Pull history from DB (last 30 days) ──
    cutoff = datetime.now() - timedelta(days=30)
    stmt = (
        select(models.UserVitalReading)
        .where(models.UserVitalReading.user_id == user_id)
        .where(models.UserVitalReading.date >= cutoff)
        .order_by(asc(models.UserVitalReading.date))
    )
    result = await db.execute(stmt)
    readings = result.scalars().all()

    # ── Convert DB rows → dicts for the AI pipeline ──
    history_dicts = [
        {
            "bp_systolic": r.bp_systolic,
            "bp_diastolic": r.bp_diastolic,
            "sugar": r.sugar,
            "heart_rate": r.heart_rate,
        }
        for r in readings
    ]

    # ── Run AI pipeline in a thread (Gemini calls are blocking) ──
    ai_result = await asyncio.to_thread(
        full_health_check, vitals_dict, history_dicts, req.language
    )

    return ai_result
