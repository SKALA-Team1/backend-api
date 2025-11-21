#!/usr/bin/env python3
"""
Test Spring2 API with JSON payload (not multipart).
"""

import asyncio
import httpx
import base64
import os
from datetime import datetime, timezone


async def test_spring2_json():
    """Test Spring2 utterance API with JSON payload"""

    print("=" * 80)
    print("Testing Spring2 API with JSON payload")
    print("=" * 80)

    spring2_url = os.getenv("SPRING2_BASE_URL", "http://localhost:8081").rstrip('/')
    session_id = "json-test-" + os.urandom(4).hex()

    # Create dummy audio
    audio_data = b"\x00\x01" * 500  # 1000 bytes

    # Build JSON payload
    payload = {
        "speaker": "user",
        "text": "Hello, I am a backend developer",
        "utterance_index": 0,
        "audio": base64.b64encode(audio_data).decode('utf-8'),
    }

    url = f"{spring2_url}/internal/sessions/{session_id}/utterances"

    print(f"\nSpring2 URL: {spring2_url}")
    print(f"Session ID: {session_id}")
    print(f"\nJSON Payload:")
    print(f"  speaker: {payload['speaker']}")
    print(f"  text: {payload['text']}")
    print(f"  utterance_index: {payload['utterance_index']}")
    print(f"  audio: <base64 {len(payload['audio'])} chars>")

    print(f"\n{'='*80}")
    print("Sending JSON request...")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)

            print(f"Status Code: {response.status_code}")
            print(f"Response Body:")
            print(f"{response.text}")

            if response.status_code in [200, 201]:
                print(f"\n✅ SUCCESS: Spring2 accepted the JSON request!")
                print(f"Response JSON: {response.json()}")
            else:
                print(f"\n❌ FAILED: Status {response.status_code}")

    except httpx.ConnectError as e:
        print(f"\n❌ CONNECTION ERROR: {e}")
        print(f"   Make sure Spring2 is running on {spring2_url}")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_spring2_json())