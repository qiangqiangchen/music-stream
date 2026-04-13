"""File utilities."""
import hashlib
import os
from pathlib import Path
from typing import Optional
from app.core.config import settings


def safe_path_join(base_dir: Path, *paths: str) -> Path:
    """
    Safely join paths and validate they stay within base_dir.
    Raises ValueError if path tries to escape base_dir.
    """
    # 规范化基础目录
    base_dir = base_dir.resolve()

    # 过滤路径中的危险字符
    safe_paths = []
    for p in paths:
        # 移除路径遍历字符
        p = p.replace('..', '').replace('\x00', '')
        # 移除多余的斜杠
        p = p.replace('\\', '/').replace('//', '/')
        safe_paths.append(p)

    # 拼接路径
    full_path = (base_dir / Path(*safe_paths)).resolve()

    # 检查是否在基础目录内
    try:
        full_path.relative_to(base_dir)
    except ValueError:
        raise ValueError(f"Path {full_path} attempts to escape base directory {base_dir}")

    # 检查符号链接
    if full_path.is_symlink():
        real_path = full_path.resolve()
        try:
            real_path.relative_to(base_dir)
        except ValueError:
            raise ValueError(f"Symlink {full_path} points outside base directory")

    return full_path


def validate_media_file(file_path: Path) -> bool:
    """Validate that a file is a legitimate media file."""
    # 检查文件是否存在
    if not file_path.exists() or not file_path.is_file():
        return False

    # 检查文件大小（最大 500MB）
    max_size = 500 * 1024 * 1024
    if file_path.stat().st_size > max_size:
        return False

    # 检查文件扩展名
    allowed_extensions = {'.mp3', '.flac', '.wav', '.m4a', '.ogg', '.aac', '.wma', '.opus'}
    if file_path.suffix.lower() not in allowed_extensions:
        return False

    # 检查文件是否可读
    if not os.access(file_path, os.R_OK):
        return False

    return True


async def get_file_checksum(file_path: Path, algorithm: str = "sha256") -> Optional[str]:
    """Calculate file checksum."""
    try:
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception:
        return None