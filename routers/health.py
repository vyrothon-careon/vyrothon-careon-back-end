# ─────────────────────────────────────────────
# AI ROUTER — DROP ZAKARIA'S LOGIC BELOW HERE
# Do not modify the router prefix or file name
# ─────────────────────────────────────────────

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def get_health():
    return {"status": "ok", "service": "VitalWatch API"}
