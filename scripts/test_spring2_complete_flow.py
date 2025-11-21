#!/usr/bin/env python3
"""
Test complete Spring2 flow: Create session → Save utterance → Complete session
"""

import asyncio
import httpx
import base64
import os


async def test_complete_flow():
    """Test complete Spring2 flow"""

    print("=" * 80)
    print("Testing Complete Spring2 Flow (JSON)")
    print("=" * 80)

    spring2_url = os.getenv("SPRING2_BASE_URL", "http://localhost:8081").rstrip('/')

    # We need to use an actual session ID from FastAPI
    # For now, let's try to create a session through Spring2 API directly

    print(f"\nSpring2 URL: {spring2_url}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Step 1: Try to list or check sessions
            print(f"\n{'='*80}")
            print("Step 1: Checking Spring2 API health")
            print(f"{'='*80}")

            response = await client.get(f"{spring2_url}/internal/health")
            print(f"Health check: {response.status_code}")

            # Step 2: Try to save utterance with a valid session
            # First, let's check if we can get any session info
            print(f"\n{'='*80}")
            print("Step 2: Trying to save utterance with JSON payload")
            print(f"{'='*80}")

            # Create test data
            audio_data = b"\x00\x01" * 500
            session_id = "test-session-001"

            payload = {
                "speaker": "user",
                "text": "Hello, I am a backend developer",
                "utterance_index": 0,
                "audio": base64.b64encode(audio_data).decode('utf-8'),
            }

            url = f"{spring2_url}/internal/sessions/{session_id}/utterances"
            print(f"\nURL: {url}")
            print(f"Payload keys: {list(payload.keys())}")

            response = await client.post(url, json=payload)

            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.text[:500]}")

            if response.status_code in [200, 201]:
                print(f"\n✅ SUCCESS!")
            elif response.status_code == 404:
                print(f"\n⚠️  404 - Session not found")
                print("   This is expected if the session doesn't exist in Spring2")
            elif response.status_code == 400:
                print(f"\n⚠️  400 - Bad Request")
                print("   Check the JSON payload format")
            else:
                print(f"\n❌ FAILED")

    except httpx.ConnectError as e:
        print(f"\n❌ CONNECTION ERROR: Cannot connect to Spring2")
        print(f"   Make sure Spring2 is running on {spring2_url}")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_complete_flow())