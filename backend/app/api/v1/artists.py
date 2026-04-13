"""Artist endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct

from app.core.database import get_db
from app.models.track import Track
from app.api.deps import get_current_active_user
from app.models.user import User

router = APIRouter()


@router.get("")
async def list_artists(
        page: int = Query(1, ge=1),
        page_size: int = Query(30, ge=1, le=100),
        search: Optional[str] = None,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """List artists with album and track counts."""

    query = select(
        Track.artist,
        func.count(distinct(Track.album)).label('album_count'),
        func.count(Track.id).label('track_count'),
        func.min(Track.id).label('first_track_id')
    ).where(
        Track.is_valid == True,
        Track.artist.isnot(None)
    )

    if search:
        query = query.where(Track.artist.contains(search))

    query = query.group_by(Track.artist)
    query = query.order_by(Track.artist)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    artists = []
    for row in result:
        # 关键修复：返回完整的后端 URL
        cover_url = f"http://localhost:8000/api/v1/media/cover/{row.first_track_id}?size=sm"

        artists.append({
            "name": row.artist,
            "album_count": row.album_count,
            "track_count": row.track_count,
            "cover_url": cover_url
        })

    return {
        "items": artists,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 1
    }

@router.get("/{artist_name}/tracks")
async def get_artist_tracks(
    artist_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get tracks by a specific artist."""

    query = select(Track).where(
        Track.is_valid == True,
        Track.artist == artist_name
    ).order_by(Track.album, Track.track_no)

    result = await db.execute(query)
    tracks = result.scalars().all()

    return tracks