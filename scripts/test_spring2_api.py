#!/usr/bin/env python3
"""
Test Spring2 API endpoint compatibility.

This script tests the exact request format expected by Spring2's
save_utterance endpoint using curl-like inspection and httpx.
"""

import asyncio
import httpx
import os


async def test_spring2_api():
    """Test Spring2 API with actual HTTP request"""

    print("=" * 80)
    print("Testing Spring2 API compatibility")
    print("=" * 80)

    # Spring2 configuration
    spring2_url = os.getenv("SPRING2_URL", "http://localhost:8081")
    session_id = "test-session-" + os.urandom(4).hex()

    print(f"\nSpring2 URL: {spring2_url}")
    print(f"Test Session ID: {session_id}")

    # Prepare test data
    speaker = "user"
    text = "test utterance from FastAPI"
    utterance_index = 0
    audio_data = b"\x00\x00" * 1000  # Dummy PCM audio

    print(f"\nTest Parameters:")
    print(f"  speaker: {speaker}")
    print(f"  text: {text}")
    print(f"  utterance_index: {utterance_index}")
    print(f"  audio_data size: {len(audio_data)} bytes")

    # Construct the URL
    url = f"{spring2_url.rstrip('/')}/internal/sessions/{session_id}/utterances"

    print(f"\nRequest URL: {url}")

    # Prepare multipart form data
    files = {
        "speaker": (None, speaker),
        "text": (None, text),
        "utterance_index": (None, str(utterance_index)),
        "audio": ("utterance_0.wav", audio_data, "audio/wav"),
    }

    print(f"\n[Sending request to Spring2]")
    print("-" * 80)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, files=files)

            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text[:500]}")

            if response.status_code == 200 or response.status_code == 201:
                print(f"\n✓ SUCCESS: Spring2 API accepted the request")
                print(f"Response JSON: {response.json()}")
            else:
                print(f"\n✗ FAILED: Spring2 returned {response.status_code}")
                print(f"Response: {response.text}")

    except asyncio.TimeoutError:
        print(f"\n✗ TIMEOUT: Spring2 server not responding at {spring2_url}")
        print(f"  Make sure Spring2 is running on {spring2_url}")

    except httpx.ConnectError as e:
        print(f"\n✗ CONNECTION ERROR: Cannot connect to {spring2_url}")
        print(f"  Make sure Spring2 is running")
        print(f"  Error: {e}")

    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_spring2_api())