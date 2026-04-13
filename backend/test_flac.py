"""Test FLAC to MP3 conversion."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.transcoder import get_transcoder


async def test_flac_conversion():
    """Test converting a FLAC file."""
    # 找一个 FLAC 文件
    media_dir = Path("media")
    flac_files = list(media_dir.rglob("*.flac"))

    if not flac_files:
        print("No FLAC files found in media directory")
        return

    test_file = flac_files[0]
    print(f"Testing with: {test_file}")
    print(f"File exists: {test_file.exists()}")
    print(f"File size: {test_file.stat().st_size} bytes")

    transcoder = get_transcoder()

    if not transcoder.is_available():
        print("FFmpeg not available")
        return

    print(f"\nFFmpeg path: {transcoder.ffmpeg_path}")
    print("\nStarting conversion...")

    mp3_data = await transcoder.transcode_to_mp3(test_file)

    if mp3_data:
        print(f"✅ Conversion successful!")
        print(f"   MP3 size: {len(mp3_data)} bytes")

        # 保存测试文件
        output_path = Path("test_output.mp3")
        output_path.write_bytes(mp3_data)
        print(f"   Saved to: {output_path}")
    else:
        print("❌ Conversion failed")


if __name__ == "__main__":
    asyncio.run(test_flac_conversion())