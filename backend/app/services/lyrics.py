"""Lyrics extraction and parsing service."""
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.config import settings
from app.models.track import Track
from app.models.lyric import Lyric, LyricType, LyricSource
from app.utils.file_utils import safe_path_join

class LyricsService:
    """Service for handling lyrics extraction and parsing."""

    async def extract_lyrics(self, track: Track, db: AsyncSession) -> Optional[Lyric]:
        """Extract lyrics from external file or embedded tags."""

        try:
            # Try external LRC file
            lyric = await self._extract_external_lrc(track)
            if lyric:
                lyric.source = LyricSource.FILE
                db.add(lyric)
                await db.commit()
                return lyric

            # Return empty lyrics instead of None
            lyric = Lyric(
                track_id=track.id,
                type=LyricType.UNSYNCED,
                source=LyricSource.EMBEDDED,
                lrc_text="",
                json_payload=[]
            )
            return lyric

        except Exception as e:
            logger.error(f"Error extracting lyrics: {e}")
            return None

    async def _extract_external_lrc(self, track: Track) -> Optional[Lyric]:
        """Try to find external LRC file."""
        try:
            file_path = safe_path_join(settings.MEDIA_DIR, track.path)

            # Try same name .lrc
            lrc_path = file_path.with_suffix('.lrc')
            if not lrc_path.exists():
                lrc_path = file_path.with_suffix('.LRC')

            if lrc_path.exists():
                with open(lrc_path, 'r', encoding='utf-8') as f:
                    lrc_text = f.read()

                lines = self._parse_lrc(lrc_text)

                return Lyric(
                    track_id=track.id,
                    type=LyricType.SYNCED if self._is_synced(lines) else LyricType.UNSYNCED,
                    lrc_text=lrc_text,
                    json_payload=lines
                )
        except Exception as e:
            logger.error(f"Error reading LRC file: {e}")

        return None

    def _parse_lrc(self, lrc_text: str) -> List[Dict[str, Any]]:
        """Parse LRC text into structured format."""
        lines = []
        pattern = re.compile(r'\[(\d{1,2}):(\d{2})\.(\d{2,3})\]')

        for line in lrc_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('[ti:') or line.startswith('[ar:') or \
               line.startswith('[al:') or line.startswith('[by:') or line.startswith('[offset:'):
                continue

            timestamps = pattern.findall(line)
            if timestamps:
                text = pattern.sub('', line).strip()
                for ts in timestamps:
                    minutes = int(ts[0])
                    seconds = int(ts[1])
                    fraction = int(ts[2])
                    if len(ts[2]) == 2:
                        fraction *= 10
                    time_ms = (minutes * 60 + seconds) * 1000 + fraction
                    if text:
                        lines.append({'time_ms': time_ms, 'text': text})
            else:
                text = line.strip()
                if text and not text.startswith('['):
                    lines.append({'time_ms': None, 'text': text})

        lines.sort(key=lambda x: x['time_ms'] if x['time_ms'] is not None else float('inf'))
        return lines

    def _is_synced(self, lines: List[Dict[str, Any]]) -> bool:
        """Check if lyrics are synced."""
        return any(line.get('time_ms') is not None for line in lines)