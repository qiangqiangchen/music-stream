"""Media library scanner."""
import os
import hashlib
import asyncio
from pathlib import Path
from typing import List, Optional, Set
from datetime import datetime
import mutagen
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from PIL import Image
import io

from app.core.config import settings
from app.models.track import Track
from app.models.lyric import Lyric, LyricType, LyricSource
from app.utils.file_utils import safe_path_join, get_file_checksum
from loguru import logger


class MediaScanner:
    """Scanner for media library."""

    SUPPORTED_EXTENSIONS = {'.mp3', '.flac', '.m4a', '.ogg', '.wav', '.aac', '.wma'}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.supported_formats = {
            '.mp3': 'audio/mpeg',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg',
            '.wav': 'audio/wav',
        }

    async def scan_directory(self, directory: Optional[Path] = None) -> dict:
        """Scan directory for media files."""
        if directory is None:
            directory = settings.MEDIA_DIR

        stats = {
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

        # Get existing tracks
        result = await self.db.execute(select(Track))
        existing_tracks = {t.path: t for t in result.scalars().all()}

        # Scan for files
        scanned_paths = set()

        for ext in self.SUPPORTED_EXTENSIONS:
            for file_path in directory.rglob(f"*{ext}"):
                try:
                    rel_path = str(file_path.relative_to(settings.MEDIA_DIR))
                    scanned_paths.add(rel_path)

                    if rel_path in existing_tracks:
                        track = existing_tracks[rel_path]
                        # Check if file was modified
                        current_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if track.last_modified_at and track.last_modified_at >= current_mtime:
                            stats['skipped'] += 1
                            continue
                        await self._update_track(track, file_path)
                        stats['updated'] += 1
                    else:
                        await self._add_track(file_path, rel_path)
                        stats['added'] += 1

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    stats['errors'] += 1

        # Mark missing tracks as invalid
        missing_paths = set(existing_tracks.keys()) - scanned_paths
        for path in missing_paths:
            track = existing_tracks[path]
            track.is_valid = False
            stats['skipped'] += 1

        await self.db.commit()

        return stats

    async def _add_track(self, file_path: Path, rel_path: str):
        """Add new track to database."""
        track = Track(path=rel_path)
        await self._extract_metadata(track, file_path)
        self.db.add(track)
        logger.info(f"Added track: {track.artist} - {track.title}")

    async def _update_track(self, track: Track, file_path: Path):
        """Update existing track metadata."""
        await self._extract_metadata(track, file_path)
        logger.info(f"Updated track: {track.artist} - {track.title}")

    async def _extract_metadata(self, track: Track, file_path: Path):
        """Extract metadata from audio file."""
        try:
            audio = mutagen.File(file_path)

            if audio is None:
                logger.warning(f"Cannot read file: {file_path}")
                return

            # Basic info
            track.title = self._get_tag(audio, 'title', ['TIT2', '©nam']) or file_path.stem
            track.artist = self._get_tag(audio, 'artist', ['TPE1', '©ART'])
            track.album = self._get_tag(audio, 'album', ['TALB', '©alb'])
            track.album_artist = self._get_tag(audio, 'albumartist', ['TPE2', 'aART'])
            track.genre = self._get_tag(audio, 'genre', ['TCON', '©gen'])

            # Year/Date
            date_str = self._get_tag(audio, 'date', ['TDRC', '©day'])
            if date_str:
                try:
                    track.year = int(date_str[:4])
                except ValueError:
                    pass

            # Track number
            track_no = self._get_tag(audio, 'tracknumber', ['TRCK', 'trkn'])
            if track_no:
                try:
                    track.track_no = int(track_no.split('/')[0])
                except ValueError:
                    pass

            # Duration
            if hasattr(audio.info, 'length'):
                track.duration = audio.info.length

            # Bitrate
            if hasattr(audio.info, 'bitrate'):
                track.bitrate = audio.info.bitrate

            # Sample rate
            if hasattr(audio.info, 'sample_rate'):
                track.sample_rate = audio.info.sample_rate

            # Format
            track.format = file_path.suffix[1:].lower()
            track.mime_type = self.supported_formats.get(file_path.suffix.lower(), 'application/octet-stream')

            # File info
            stat = file_path.stat()
            track.size = stat.st_size
            track.last_modified_at = datetime.fromtimestamp(stat.st_mtime)
            track.checksum = await get_file_checksum(file_path)

            # Check for embedded cover
            track.has_embedded_cover = self._has_embedded_cover(audio)

            track.is_valid = True

        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            track.is_valid = False

    def _get_tag(self, audio, default_key: str, possible_keys: List[str]) -> Optional[str]:
        """Get tag value from audio file."""
        if isinstance(audio, mutagen.id3.ID3):
            for key in possible_keys:
                if key in audio:
                    return str(audio[key])
        elif isinstance(audio, mutagen.mp4.MP4):
            for key in possible_keys:
                if key in audio:
                    return str(audio[key][0])
        elif hasattr(audio, 'get'):
            value = audio.get(default_key)
            if value:
                return str(value[0]) if isinstance(value, list) else str(value)
        return None

    def _has_embedded_cover(self, audio) -> bool:
        """Check if audio has embedded cover art."""
        try:
            if isinstance(audio, ID3):
                return 'APIC:' in audio
            elif isinstance(audio, FLAC):
                return len(audio.pictures) > 0
            elif isinstance(audio, MP4):
                return 'covr' in audio
        except:
            pass
        return False


class CoverExtractor:
    """Extract and cache cover images."""

    async def extract_cover_data(self, track: Track) -> Optional[bytes]:
        """Extract cover data from audio file."""
        try:
            file_path = safe_path_join(settings.MEDIA_DIR, track.path)

            # 尝试从音频文件中提取
            audio = mutagen.File(file_path)
            if audio:
                # MP3
                if isinstance(audio, ID3):
                    for key in audio:
                        if key.startswith('APIC'):
                            return audio[key].data

                # FLAC
                elif hasattr(audio, 'pictures') and audio.pictures:
                    return audio.pictures[0].data

                # MP4/M4A
                elif hasattr(audio, 'get') and 'covr' in audio:
                    return bytes(audio['covr'][0])

            # 尝试从文件夹中查找封面
            folder = file_path.parent
            for cover_name in ['cover.jpg', 'cover.png', 'folder.jpg', 'front.jpg', 'album.jpg']:
                cover_path = folder / cover_name
                if cover_path.exists():
                    with open(cover_path, 'rb') as f:
                        return f.read()

        except Exception as e:
            logger.error(f"Error extracting cover: {e}")

        return None

    async def get_or_generate_cover(self, track: Track, size: str = "lg") -> Optional[Path]:
        """Get or generate cover image for track."""
        cache_key = f"{track.id}_{track.checksum}_{size}"
        cache_path = settings.CACHE_DIR / "covers" / f"{cache_key}.jpg"

        # Return cached if exists
        if cache_path.exists():
            return cache_path

        # Try to extract cover
        cover_data = await self._extract_cover(track)

        if cover_data:
            # Resize if needed
            if size == "sm":
                cover_data = self._resize_image(cover_data, (100, 100))
            elif size == "lg":
                cover_data = self._resize_image(cover_data, (500, 500))

            # Save to cache
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'wb') as f:
                f.write(cover_data)

            return cache_path

        return None

    async def _extract_cover(self, track: Track) -> Optional[bytes]:
        """Extract cover from audio file or folder."""
        file_path = safe_path_join(settings.MEDIA_DIR, track.path)

        # Try embedded cover
        try:
            audio = mutagen.File(file_path)
            if audio:
                cover_data = self._get_embedded_cover(audio)
                if cover_data:
                    return cover_data
        except:
            pass

        # Try folder cover
        folder = file_path.parent
        for cover_name in ['cover.jpg', 'cover.png', 'folder.jpg', 'folder.png', 'front.jpg']:
            cover_path = folder / cover_name
            if cover_path.exists():
                with open(cover_path, 'rb') as f:
                    return f.read()

        return None

    def _get_embedded_cover(self, audio) -> Optional[bytes]:
        """Get embedded cover art."""
        try:
            if isinstance(audio, ID3):
                for key in audio:
                    if key.startswith('APIC'):
                        return audio[key].data
            elif isinstance(audio, FLAC):
                if audio.pictures:
                    return audio.pictures[0].data
            elif isinstance(audio, MP4):
                if 'covr' in audio:
                    return bytes(audio['covr'][0])
        except:
            pass
        return None

    def _resize_image(self, image_data: bytes, size: tuple) -> bytes:
        """Resize image to specified size."""
        img = Image.open(io.BytesIO(image_data))
        img.thumbnail(size, Image.Resampling.LANCZOS)

        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        return output.getvalue()