"""Test FFmpeg installation."""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.transcoder import get_transcoder


def test_ffmpeg():
    """Test if FFmpeg is found and working."""
    transcoder = get_transcoder()

    if transcoder.is_available():
        print(f"✅ FFmpeg found at: {transcoder.ffmpeg_path}")

        # 测试运行 ffmpeg
        import subprocess
        try:
            result = subprocess.run(
                [transcoder.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("✅ FFmpeg can run successfully")
                # 显示版本信息的第一行
                version_line = result.stdout.split('\n')[0]
                print(f"   Version: {version_line}")
            else:
                print("❌ FFmpeg failed to run")
        except Exception as e:
            print(f"❌ Error running FFmpeg: {e}")
    else:
        print("❌ FFmpeg not found!")
        print("\nChecked locations:")
        print("  - System PATH")
        print("  - backend/bin/ffmpeg.exe")
        print("  - backend/ffmpeg.exe")
        print("  - C:/ffmpeg/bin/ffmpeg.exe")


if __name__ == "__main__":
    test_ffmpeg()