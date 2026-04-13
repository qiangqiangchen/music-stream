"""Audio transcoding service with caching."""
import asyncio
import tempfile
import subprocess
import hashlib
from pathlib import Path
from typing import Optional
from loguru import logger

from app.core.config import settings

class AudioTranscoder:
    """Transcode audio files to MP3 with caching."""

    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.cache_dir = settings.DATA_DIR / "transcode_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if self.ffmpeg_path:
            logger.info(f"FFmpeg found: {self.ffmpeg_path}")
            logger.info(f"Cache directory: {self.cache_dir}")
        else:
            logger.warning("FFmpeg not found, transcoding disabled")

    def _find_ffmpeg(self) -> Optional[str]:
        """Find ffmpeg executable."""
        import shutil

        # 检查系统 PATH
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            return ffmpeg

        # 检查 bin 目录
        bin_ffmpeg = Path(__file__).parent.parent.parent / "bin" / "ffmpeg.exe"
        if bin_ffmpeg.exists():
            return str(bin_ffmpeg)

        # 检查当前目录
        local_ffmpeg = Path(__file__).parent.parent.parent / "ffmpeg.exe"
        if local_ffmpeg.exists():
            return str(local_ffmpeg)

        return None

    def is_available(self) -> bool:
        """Check if transcoder is available."""
        return self.ffmpeg_path is not None

    def _get_cache_key(self, input_path: Path) -> str:
        """Generate cache key based on file path and modified time."""
        stat = input_path.stat()
        key_str = f"{input_path}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached_path(self, cache_key: str) -> Path:
        """Get cached file path."""
        return self.cache_dir / f"{cache_key}.mp3"

    async def transcode_to_mp3(self, input_path: Path) -> Optional[bytes]:
        """Transcode audio to MP3 format with caching."""
        if not self.ffmpeg_path:
            logger.error("Cannot transcode: FFmpeg not available")
            return None

        # 检查缓存
        cache_key = self._get_cache_key(input_path)
        cached_path = self._get_cached_path(cache_key)

        if cached_path.exists():
            logger.info(f"Using cached transcode: {cached_path}")
            try:
                with open(cached_path, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading cache: {e}")
                # 缓存读取失败，继续转码

        logger.info(f"Transcoding: {input_path}")

        try:
            # 创建临时输出文件
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                output_path = Path(tmp.name)

            # 转码命令
            cmd = [
                self.ffmpeg_path,
                '-i', str(input_path),
                '-vn',
                '-acodec', 'libmp3lame',
                '-ab', '192k',
                '-ar', '44100',
                '-ac', '2',
                '-y',
                str(output_path)
            ]

            logger.info(f"Running FFmpeg...")

            # 执行转码
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120  # 增加超时时间
            )

            if result.returncode == 0 and output_path.exists():
                # 读取数据
                with open(output_path, 'rb') as f:
                    data = f.read()

                # 保存到缓存
                try:
                    with open(cached_path, 'wb') as f:
                        f.write(data)
                    logger.info(f"Cached to: {cached_path}")
                except Exception as e:
                    logger.error(f"Error saving cache: {e}")

                # 清理临时文件
                output_path.unlink()

                logger.info(f"Transcode successful: {len(data)} bytes")
                return data
            else:
                if result.stderr:
                    error_msg = result.stderr.decode('utf-8', errors='ignore')
                    logger.error(f"FFmpeg error: {error_msg[:500]}")
                if output_path.exists():
                    output_path.unlink()
                return None

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout")
            return None
        except Exception as e:
            logger.error(f"Transcoding error: {e}", exc_info=True)
            return None

    def get_cache_info(self) -> dict:
        """Get cache information."""
        cache_files = list(self.cache_dir.glob("*.mp3"))
        total_size = sum(f.stat().st_size for f in cache_files)
        return {
            "count": len(cache_files),
            "total_size": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "directory": str(self.cache_dir)
        }

    def clear_cache(self) -> int:
        """Clear all cached files."""
        count = 0
        for cache_file in self.cache_dir.glob("*.mp3"):
            try:
                cache_file.unlink()
                count += 1
            except Exception as e:
                logger.error(f"Error deleting cache {cache_file}: {e}")
        logger.info(f"Cleared {count} cache files")
        return count


# 全局实例
_transcoder = None

def get_transcoder() -> AudioTranscoder:
    """Get or create transcoder instance."""
    global _transcoder
    if _transcoder is None:
        _transcoder = AudioTranscoder()
    return _transcoder