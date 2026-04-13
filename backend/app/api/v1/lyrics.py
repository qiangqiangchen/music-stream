"""Lyrics endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.track import Track
from app.models.lyric import Lyric, LyricType, LyricSource
from app.schemas.lyric import LyricResponse, LyricLine
from app.services.lyrics import LyricsService
from app.api.deps import get_current_active_user
from app.models.user import User
from loguru import logger

router = APIRouter()

@router.get("/{track_id}")
async def get_lyrics(
    track_id: int,
    format: str = Query("json", regex="^(json|lrc)$"),
    offset: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get lyrics for a track."""

    try:
        # Get track
        result = await db.execute(select(Track).where(Track.id == track_id))
        track = result.scalar_one_or_none()

        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        # Try to get cached lyrics
        result = await db.execute(select(Lyric).where(Lyric.track_id == track_id))
        lyric = result.scalar_one_or_none()

        if not lyric:
            # Extract lyrics
            lyrics_service = LyricsService()
            lyric = await lyrics_service.extract_lyrics(track, db)

        if not lyric:
            # Return empty response
            if format == "lrc":
                return Response(content="", media_type="text/plain")
            return LyricResponse(
                track_id=track_id,
                type=LyricType.UNSYNCED,
                source=LyricSource.EMBEDDED,
                lines=[],
                offset_ms=track.lyrics_offset_ms
            )

        # Apply offset
        total_offset = track.lyrics_offset_ms + (offset or 0)

        if format == "lrc":
            if lyric.lrc_text:
                return Response(content=lyric.lrc_text, media_type="text/plain")
            return Response(content="", media_type="text/plain")

        # JSON format
        lines = []
        if lyric.json_payload:
            for line_data in lyric.json_payload:
                time_ms = line_data.get('time_ms')
                if time_ms is not None and total_offset != 0:
                    time_ms = max(0, time_ms + total_offset)
                lines.append(LyricLine(time_ms=time_ms, text=line_data['text']))

        return LyricResponse(
            track_id=track_id,
            type=lyric.type,
            source=lyric.source,
            lrc_text=lyric.lrc_text if format == "json" else None,
            lines=lines,
            offset_ms=track.lyrics_offset_ms
        )

    except Exception as e:
        logger.error(f"Error getting lyrics: {e}")
        # Return empty lyrics on error
        return LyricResponse(
            track_id=track_id,
            type=LyricType.UNSYNCED,
            source=LyricSource.EMBEDDED,
            lines=[],
            offset_ms=0
        )