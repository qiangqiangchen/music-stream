"""Track endpoints."""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlmodel import and_, or_

from app.core.database import get_db
from app.models.track import Track
from app.schemas.track import TrackResponse, TrackListResponse
from app.api.deps import get_current_active_user

router = APIRouter()


@router.get("", response_model=TrackListResponse)
async def list_tracks(
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
        search: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        genre: Optional[str] = None,
        sort_by: str = Query("title", regex="^(title|artist|album|year|duration)$"),
        sort_order: str = Query("asc", regex="^(asc|desc)$"),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_active_user)
):
    """List tracks with filtering and pagination."""

    # Build query
    query = select(Track).where(Track.is_valid == True)

    # Apply filters
    if search:
        query = query.where(
            or_(
                Track.title.contains(search),
                Track.artist.contains(search),
                Track.album.contains(search)
            )
        )
    if artist:
        query = query.where(Track.artist.contains(artist))
    if album:
        query = query.where(Track.album.contains(album))
    if genre:
        query = query.where(Track.genre == genre)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply sorting
    sort_column = getattr(Track, sort_by)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute
    result = await db.execute(query)
    tracks = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return TrackListResponse(
        items=tracks,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{track_id}", response_model=TrackResponse)
async def get_track(
        track_id: int,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_active_user)
):
    """Get track by ID."""
    result = await db.execute(
        select(Track).where(
            Track.id == track_id,
            Track.is_valid == True
        )
    )
    track = result.scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    return track


