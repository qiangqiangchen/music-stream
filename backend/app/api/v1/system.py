"""System management endpoints."""
from fastapi import APIRouter, Depends
from app.services.transcoder import get_transcoder
from app.api.deps import get_current_admin_user
from app.models.user import User

router = APIRouter()

@router.get("/cache/info")
async def get_cache_info(
    current_user: User = Depends(get_current_admin_user)
):
    """Get transcode cache information (admin only)."""
    transcoder = get_transcoder()
    return transcoder.get_cache_info()

@router.post("/cache/clear")
async def clear_cache(
    current_user: User = Depends(get_current_admin_user)
):
    """Clear transcode cache (admin only)."""
    transcoder = get_transcoder()
    count = transcoder.clear_cache()
    return {"message": f"Cleared {count} cache files"}