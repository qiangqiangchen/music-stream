from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.models.track import Track
from app.api.deps import get_current_active_user
from app.utils.file_utils import safe_path_join

import mimetypes
import aiofiles
from fastapi.responses import FileResponse, Response, StreamingResponse
router = APIRouter()

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import Image
    import ImageDraw
    import ImageFont


@router.get("/stream/{track_id}")
async def stream_track(
        track_id: int,
        request: Request,
        transcode: bool = False,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_active_user)
):
    """Stream audio file with optional transcoding."""
    from app.services.transcoder import get_transcoder

    # Get track
    result = await db.execute(
        select(Track).where(
            Track.id == track_id,
            Track.is_valid == True
        )
    )
    track = result.scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # Build file path
    try:
        file_path = safe_path_join(settings.MEDIA_DIR, track.path)
        logger.info(f"Stream request - Track: {track.title}, Format: {track.format}, Transcode: {transcode}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # 如果需要转码且是 FLAC 格式
    if transcode and track.format == 'flac':
        logger.info(f"FLAC file detected, attempting transcode: {file_path}")
        transcoder = get_transcoder()

        if transcoder.is_available():
            logger.info(f"Starting transcode to MP3...")
            mp3_data = await transcoder.transcode_to_mp3(file_path)

            if mp3_data:
                logger.info(f"Transcode successful, returning MP3 data ({len(mp3_data)} bytes)")
                # 关键：返回转码后的 MP3 数据
                return Response(
                    content=mp3_data,
                    media_type="audio/mpeg",
                    headers={
                        "Content-Length": str(len(mp3_data)),
                        "Accept-Ranges": "bytes",
                        "Content-Type": "audio/mpeg",
                        "Cache-Control": "no-cache"
                    }
                )
            else:
                logger.error("Transcode failed, falling back to original file")
        else:
            logger.warning("FFmpeg not available, serving original FLAC file")

    # 正常流式传输（非转码或转码失败时）
    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    # 确定 MIME 类型
    mime_type = 'audio/mpeg' if track.format == 'mp3' else mimetypes.guess_type(str(file_path))[0]

    logger.info(f"Serving original file: {file_path}, MIME: {mime_type}")

    if not range_header:
        return FileResponse(
            path=str(file_path),
            media_type=mime_type or "application/octet-stream",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Cache-Control": "no-cache"
            }
        )

    # 处理 Range 请求
    try:
        range_str = range_header.replace("bytes=", "")
        ranges = range_str.split("-")
        start = int(ranges[0]) if ranges[0] else 0
        end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1

        if start >= file_size or end >= file_size or start > end:
            raise ValueError("Invalid range")

    except ValueError:
        raise HTTPException(status_code=416, detail="Range Not Satisfiable")

    chunk_size = end - start + 1

    async def file_iterator():
        async with aiofiles.open(file_path, 'rb') as f:
            await f.seek(start)
            bytes_read = 0
            while bytes_read < chunk_size:
                read_size = min(64 * 1024, chunk_size - bytes_read)
                chunk = await f.read(read_size)
                if not chunk:
                    break
                yield chunk
                bytes_read += len(chunk)

    return StreamingResponse(
        file_iterator(),
        status_code=206,
        media_type=mime_type or "application/octet-stream",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Cache-Control": "no-cache"
        }
    )


@router.get("/download/{track_id}")
async def download_track(
        track_id: int,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_active_user)
):
    """Download track file."""
    if not settings.ALLOW_DOWNLOAD:
        raise HTTPException(status_code=403, detail="Downloads are disabled")

    result = await db.execute(
        select(Track).where(
            Track.id == track_id,
            Track.is_valid == True
        )
    )
    track = result.scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    try:
        file_path = safe_path_join(settings.MEDIA_DIR, track.path)
        logger.info(f"Download: {file_path}")
    except ValueError as e:
        logger.error(f"Invalid path: {e}")
        raise HTTPException(status_code=400, detail="Invalid path")

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")

    # 构建安全的文件名
    safe_filename = f"{track.artist or 'Unknown'} - {track.title}.{track.format}"
    # 移除不安全的字符
    import re
    safe_filename = re.sub(r'[<>:"/\\|?*]', '', safe_filename)

    logger.info(f"Download filename: {safe_filename}")

    # 返回文件
    return FileResponse(
        path=str(file_path),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename.encode("ascii", "ignore").decode()}"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@router.head("/stream/{track_id}")
async def head_stream_track(
    track_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """HEAD request for stream endpoint."""
    result = await db.execute(
        select(Track).where(
            Track.id == track_id,
            Track.is_valid == True
        )
    )
    track = result.scalar_one_or_none()
    
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        file_path = safe_path_join(settings.MEDIA_DIR, track.path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    mime_type = 'audio/mpeg' if track.format == 'mp3' else mimetypes.guess_type(str(file_path))[0]
    
    return Response(
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_path.stat().st_size),
            "Content-Type": mime_type or "application/octet-stream"
        }
    )


@router.get("/cover/{track_id}")
async def get_cover(
        track_id: int,
        size: str = "sm",
        db: AsyncSession = Depends(get_db)
):
    """Get cover image for track."""
    from PIL import Image, ImageDraw, ImageFont
    import io
    import mutagen
    from mutagen.id3 import ID3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4

    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    cover_data = None

    # 尝试从音频文件提取封面
    try:
        file_path = safe_path_join(settings.MEDIA_DIR, track.path)

        if file_path.exists():
            audio = mutagen.File(file_path)
            if audio:
                # MP3
                if isinstance(audio, ID3):
                    for key in audio:
                        if key.startswith('APIC'):
                            cover_data = audio[key].data
                            logger.info(f"Found embedded cover in MP3: {track.title}")
                            break

                # FLAC
                elif isinstance(audio, FLAC) and audio.pictures:
                    cover_data = audio.pictures[0].data
                    logger.info(f"Found embedded cover in FLAC: {track.title}")

                # MP4/M4A
                elif isinstance(audio, MP4) and 'covr' in audio:
                    cover_data = bytes(audio['covr'][0])
                    logger.info(f"Found embedded cover in M4A: {track.title}")

            # 尝试从文件夹找封面
            if not cover_data:
                folder = file_path.parent
                for cover_name in ['cover.jpg', 'cover.png', 'folder.jpg', 'front.jpg', 'album.jpg', 'albumart.jpg']:
                    cover_path = folder / cover_name
                    if cover_path.exists():
                        with open(cover_path, 'rb') as f:
                            cover_data = f.read()
                        logger.info(f"Found folder cover: {cover_path}")
                        break
    except Exception as e:
        logger.error(f"Error extracting cover: {e}")

    # 处理封面图片
    if cover_data:
        try:
            img = Image.open(io.BytesIO(cover_data))

            # 调整大小
            if size == "sm":
                target_size = (100, 100)
            else:
                target_size = (500, 500)

            # 保持宽高比
            img.thumbnail(target_size, Image.Resampling.LANCZOS)

            # 转换为 RGB
            if img.mode in ('RGBA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img

            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85)

            return Response(
                content=output.getvalue(),
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=31536000"}
            )
        except Exception as e:
            logger.error(f"Error processing cover image: {e}")

    # 生成默认封面
    logger.info(f"Generating default cover for: {track.title}")
    return generate_default_cover(track, size)


def generate_default_cover(track: Track, size: str = "sm"):
    """Generate a default cover image with track info."""
    from PIL import Image, ImageDraw, ImageFont
    import io
    import random

    # 根据尺寸设置图片大小
    img_size = 500 if size == "lg" else 100

    # 创建图片
    img = Image.new('RGB', (img_size, img_size), color=_get_color_for_text(track.title))
    draw = ImageDraw.Draw(img)

    # 绘制音乐符号
    if img_size >= 100:
        try:
            # 尝试使用系统字体
            font_size = img_size // 3
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        # 绘制音乐符号
        text = "♪"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (img_size - text_width) // 2
        y = (img_size - text_height) // 3
        draw.text((x, y), text, fill='white', font=font)

        # 绘制曲目名称（仅大图）
        if img_size >= 500:
            title = track.title[:15] + "..." if len(track.title) > 15 else track.title
            try:
                small_font = ImageFont.truetype("arial.ttf", 24)
            except:
                small_font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), title, font=small_font)
            text_width = bbox[2] - bbox[0]
            x = (img_size - text_width) // 2
            y = img_size * 2 // 3
            draw.text((x, y), title, fill='rgba(255,255,255,0.9)', font=small_font)

    # 保存为字节流
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)

    return Response(
        content=output.getvalue(),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000"}
    )


def _get_color_for_text(text: str) -> tuple:
    """Generate a consistent color based on text."""
    import hashlib
    hash_val = int(hashlib.md5(text.encode()).hexdigest()[:6], 16)

    # 生成柔和的颜色
    r = (hash_val & 0xFF0000) >> 16
    g = (hash_val & 0x00FF00) >> 8
    b = hash_val & 0x0000FF

    # 调暗一点，更适合做背景
    r = int(r * 0.6)
    g = int(g * 0.6)
    b = int(b * 0.6)

    return (r, g, b)