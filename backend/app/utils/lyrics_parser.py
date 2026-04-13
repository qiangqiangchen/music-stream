"""LRC and lyrics parsing utilities."""
import re
from typing import List, Dict, Any, Optional

# LRC timestamp pattern: [mm:ss.xx] or [mm:ss.xxx]
LRC_TIMESTAMP_PATTERN = re.compile(r'\[(\d{1,2}):(\d{2})\.(\d{2,3})\]')


def parse_lrc(lrc_text: str) -> List[Dict[str, Any]]:
    """Parse LRC text into structured format."""
    lines = []

    # Extract offset if present
    offset_match = re.search(r'\[offset:([+-]?\d+)\]', lrc_text)
    offset_ms = int(offset_match.group(1)) if offset_match else 0

    for line in lrc_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Skip metadata tags
        if line.startswith('[ti:') or line.startswith('[ar:') or \
                line.startswith('[al:') or line.startswith('[by:') or \
                line.startswith('[offset:'):
            continue

        # Find all timestamps in line
        timestamps = LRC_TIMESTAMP_PATTERN.findall(line)

        if timestamps:
            # Extract text after all timestamps
            text = LRC_TIMESTAMP_PATTERN.sub('', line).strip()

            for ts in timestamps:
                minutes = int(ts[0])
                seconds = int(ts[1])
                fraction = int(ts[2])

                # Convert to milliseconds
                if len(ts[2]) == 2:  # centiseconds
                    fraction *= 10

                time_ms = (minutes * 60 + seconds) * 1000 + fraction
                time_ms += offset_ms

                if text:  # Only add if there's text
                    lines.append({'time_ms': max(0, time_ms), 'text': text})
        else:
            # Line without timestamp (unsynced)
            text = line.strip()
            if text and not text.startswith('['):
                lines.append({'time_ms': None, 'text': text})

    # Sort by timestamp
    lines.sort(key=lambda x: x['time_ms'] if x['time_ms'] is not None else float('inf'))

    return lines


def parse_sylt(sylt) -> List[Dict[str, Any]]:
    """Parse ID3 SYLT frame."""
    lines = []

    try:
        # SYLT format: text encoding, language, timestamp format, content type,
        # then sync data: (null-terminated text, timestamp)
        data = sylt.data

        # Skip header (first 6 bytes)
        pos = 6

        while pos < len(data):
            # Read null-terminated text
            text_bytes = bytearray()
            while pos < len(data) and data[pos] != 0:
                text_bytes.append(data[pos])
                pos += 1
            pos += 1  # Skip null terminator

            if pos + 4 > len(data):
                break

            # Read timestamp (4 bytes, big-endian)
            timestamp = int.from_bytes(data[pos:pos + 4], 'big')
            pos += 4

            try:
                text = text_bytes.decode('utf-8')
            except:
                text = text_bytes.decode('latin-1')

            if text.strip():
                lines.append({'time_ms': timestamp, 'text': text.strip()})

    except Exception as e:
        print(f"Error parsing SYLT: {e}")

    return lines