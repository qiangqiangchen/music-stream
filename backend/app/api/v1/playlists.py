"""Playlist endpoints."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.playlist import Playlist, PlaylistItem
from app.models.track import Track
from app.models.user import User
from app.api.deps import get_current_active_user
from loguru import logger

router = APIRouter()


class PlaylistCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False


class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class TrackAdd(BaseModel):
    track_id: int


class TracksReorder(BaseModel):
    track_ids: List[int]


# 获取当前用户的所有播放列表
@router.get("")
async def get_playlists(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get user's playlists."""
    query = select(Playlist).where(
        Playlist.user_id == current_user.id
    ).order_by(Playlist.updated_at.desc())

    result = await db.execute(query)
    playlists = result.scalars().all()

    # 获取每个播放列表的歌曲数量
    playlist_data = []
    for pl in playlists:
        count_result = await db.execute(
            select(func.count()).select_from(PlaylistItem).where(PlaylistItem.playlist_id == pl.id)
        )
        track_count = count_result.scalar() or 0

        playlist_data.append({
            "id": pl.id,
            "name": pl.name,
            "description": pl.description,
            "is_public": pl.is_public,
            "track_count": track_count,
            "created_at": pl.created_at.isoformat(),
            "updated_at": pl.updated_at.isoformat()
        })

    return playlist_data


# 创建播放列表
@router.post("")
async def create_playlist(
        data: PlaylistCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Create a new playlist."""
    playlist = Playlist(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        is_public=data.is_public
    )

    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)

    logger.info(f"Playlist created: {playlist.name} by {current_user.username}")

    return {
        "id": playlist.id,
        "name": playlist.name,
        "description": playlist.description,
        "is_public": playlist.is_public,
        "track_count": 0,
        "created_at": playlist.created_at.isoformat(),
        "updated_at": playlist.updated_at.isoformat()
    }


# 获取单个播放列表详情
@router.get("/{playlist_id}")
async def get_playlist(
        playlist_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get playlist details with tracks."""
    # 获取播放列表
    playlist_result = await db.execute(
        select(Playlist).where(
            and_(
                Playlist.id == playlist_id,
                Playlist.user_id == current_user.id
            )
        )
    )
    playlist = playlist_result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # 获取播放列表中的歌曲 - 返回完整信息
    items_result = await db.execute(
        select(PlaylistItem, Track).join(
            Track, PlaylistItem.track_id == Track.id
        ).where(
            PlaylistItem.playlist_id == playlist_id
        ).order_by(PlaylistItem.position)
    )

    tracks = []
    for item, track in items_result:
        tracks.append({
            "id": track.id,
            "title": track.title,
            "artist": track.artist,
            "album": track.album,
            "duration": track.duration,
            "format": track.format,  # 重要：格式信息
            "bitrate": track.bitrate,
            "size": track.size,
            "position": item.position,
            "added_at": item.added_at.isoformat()
        })

    return {
        "id": playlist.id,
        "name": playlist.name,
        "description": playlist.description,
        "is_public": playlist.is_public,
        "tracks": tracks,
        "created_at": playlist.created_at.isoformat(),
        "updated_at": playlist.updated_at.isoformat()
    }

# 更新播放列表
@router.put("/{playlist_id}")
async def update_playlist(
        playlist_id: int,
        data: PlaylistUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Update playlist."""
    result = await db.execute(
        select(Playlist).where(
            and_(
                Playlist.id == playlist_id,
                Playlist.user_id == current_user.id
            )
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    if data.name is not None:
        playlist.name = data.name
    if data.description is not None:
        playlist.description = data.description
    if data.is_public is not None:
        playlist.is_public = data.is_public

    playlist.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(playlist)

    return {"message": "Playlist updated"}


# 删除播放列表
@router.delete("/{playlist_id}")
async def delete_playlist(
        playlist_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Delete playlist."""
    result = await db.execute(
        select(Playlist).where(
            and_(
                Playlist.id == playlist_id,
                Playlist.user_id == current_user.id
            )
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    await db.delete(playlist)
    await db.commit()

    logger.info(f"Playlist deleted: {playlist.name}")

    return {"message": "Playlist deleted"}


# 添加歌曲到播放列表
@router.post("/{playlist_id}/tracks")
async def add_track_to_playlist(
        playlist_id: int,
        data: TrackAdd,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Add track to playlist."""
    # 验证播放列表所有权
    playlist_result = await db.execute(
        select(Playlist).where(
            and_(
                Playlist.id == playlist_id,
                Playlist.user_id == current_user.id
            )
        )
    )
    playlist = playlist_result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # 验证歌曲存在
    track_result = await db.execute(
        select(Track).where(Track.id == data.track_id, Track.is_valid == True)
    )
    track = track_result.scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # 检查是否已存在
    existing_result = await db.execute(
        select(PlaylistItem).where(
            and_(
                PlaylistItem.playlist_id == playlist_id,
                PlaylistItem.track_id == data.track_id
            )
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        return {"message": "Track already in playlist"}

    # 获取最大位置
    pos_result = await db.execute(
        select(func.max(PlaylistItem.position)).where(PlaylistItem.playlist_id == playlist_id)
    )
    max_pos = pos_result.scalar() or -1

    # 添加歌曲
    item = PlaylistItem(
        playlist_id=playlist_id,
        track_id=data.track_id,
        position=max_pos + 1
    )

    db.add(item)

    # 更新播放列表时间
    playlist.updated_at = datetime.utcnow()

    await db.commit()

    return {"message": "Track added to playlist"}


# 从播放列表中移除歌曲
@router.delete("/{playlist_id}/tracks/{track_id}")
async def remove_track_from_playlist(
        playlist_id: int,
        track_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Remove track from playlist."""
    # 验证播放列表所有权
    playlist_result = await db.execute(
        select(Playlist).where(
            and_(
                Playlist.id == playlist_id,
                Playlist.user_id == current_user.id
            )
        )
    )
    playlist = playlist_result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # 删除
    await db.execute(
        delete(PlaylistItem).where(
            and_(
                PlaylistItem.playlist_id == playlist_id,
                PlaylistItem.track_id == track_id
            )
        )
    )

    # 更新播放列表时间
    playlist.updated_at = datetime.utcnow()

    await db.commit()

    return {"message": "Track removed from playlist"}


# 重新排序播放列表
@router.put("/{playlist_id}/tracks/reorder")
async def reorder_playlist_tracks(
        playlist_id: int,
        data: TracksReorder,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Reorder tracks in playlist."""
    # 验证播放列表所有权
    playlist_result = await db.execute(
        select(Playlist).where(
            and_(
                Playlist.id == playlist_id,
                Playlist.user_id == current_user.id
            )
        )
    )
    playlist = playlist_result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # 更新位置
    for idx, track_id in enumerate(data.track_ids):
        result = await db.execute(
            select(PlaylistItem).where(
                and_(
                    PlaylistItem.playlist_id == playlist_id,
                    PlaylistItem.track_id == track_id
                )
            )
        )
        item = result.scalar_one_or_none()
        if item:
            item.position = idx

    playlist.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Playlist reordered"}