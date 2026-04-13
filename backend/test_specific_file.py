"""Test specific FLAC file."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.transcoder import get_transcoder

async def test_specific_file():
    """Test the specific FLAC file."""
    test_file = Path("media/周杰伦/七里香/七里香.flac")

    if not test_file.exists():
        print(f"File not found: {test_file}")
        return

    print(f"Testing: {test_file}")
    print(f"Size: {test_file.stat().st_size} bytes")

    transcoder = get_transcoder()

    if not transcoder.is_available():
        print("FFmpeg not available")
        return

    print("\nStarting conversion...")
    mp3_data = await transcoder.transcode_to_mp3(test_file)

    if mp3_data:
        print(f"✅ Success: {len(mp3_data)} bytes")
        output_path = Path("test_output.mp3")
        output_path.write_bytes(mp3_data)
        print(f"Saved to: {output_path.absolute()}")
    else:
        print("❌ Failed")

if __name__ == "__main__":
    asyncio.run(test_specific_file())