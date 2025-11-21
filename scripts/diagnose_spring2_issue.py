#!/usr/bin/env python3
"""
Comprehensive diagnostic script for Spring2 integration issues.

This script helps diagnose what's happening with the Spring2 API calls
by inspecting the actual request being sent and providing detailed feedback.
"""

import asyncio
import httpx
import sys
from datetime import datetime, timezone
import os


async def main():
    """Run comprehensive Spring2 diagnostics"""

    print("=" * 80)
    print("SKALA Spring2 Integration Diagnostics")
    print("=" * 80)

    # Get Spring2 URL from environment or use default
    spring2_url = os.getenv("SPRING2_BASE_URL", "http://localhost:8082").rstrip('/')
    session_id = "diagnostic-" + os.urandom(4).hex()

    print(f"\nConfiguration:")
    print(f"  Spring2 URL: {spring2_url}")
    print(f"  Test Session ID: {session_id}")
    print(f"  Test Endpoint: {spring2_url}/internal/sessions/{session_id}/utterances")

    # Test data
    speaker = "user"
    text = "test utterance from diagnostic"
    utterance_index = 0
    audio_data = b"\x00\x01\x02\x03" * 250  # 1000 bytes of dummy audio

    print(f"\nTest Data:")
    print(f"  speaker: '{speaker}'")
    print(f"  text: '{text}'")
    print(f"  utterance_index: {utterance_index}")
    print(f"  audio_data size: {len(audio_data)} bytes")

    # Build the request exactly as spring2_client.save_utterance() does
    print(f"\n{'='*80}")
    print("STEP 1: Building Request (like spring2_client.save_utterance)")
    print(f"{'='*80}")

    # Normalize speaker
    normalized_speaker = (speaker or "user").lower()

    # Build files dict (exactly as in spring2_client.py)
    files = {
        "speaker": (None, normalized_speaker),
        "text": (None, text),
        "utterance_index": (None, str(utterance_index)),
        "audio": (f"utterance_{utterance_index}.wav", audio_data, "audio/wav"),
    }

    print(f"\nFiles parameter structure:")
    for key, value in files.items():
        if key == "audio":
            print(f"  {key}: ({value[0]!r}, <{len(value[1])} bytes>, {value[2]!r})")
        else:
            print(f"  {key}: {value}")

    # Build the request
    url = f"{spring2_url}/internal/sessions/{session_id}/utterances"

    print(f"\nRequest URL: {url}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # First, build the request to inspect it
        req = client.build_request("POST", url, files=files)

        print(f"\nRequest Headers:")
        for header, value in req.headers.items():
            if header.lower() == "content-type":
                print(f"  {header}: {value}")
                if "multipart" in value:
                    print(f"    ✓ Correctly using multipart/form-data")
                else:
                    print(f"    ✗ ERROR: Not using multipart/form-data!")
            elif header.lower() == "content-length":
                print(f"  {header}: {value}")

        # Inspect the body
        print(f"\n{'='*80}")
        print("STEP 2: Inspecting Request Body")
        print(f"{'='*80}")

        body = b""
        for chunk in req.stream:
            body += chunk

        body_str = body.decode('utf-8', errors='replace')

        # Check for required fields
        print(f"\nField Presence Check:")
        fields_to_check = ['speaker', 'text', 'utterance_index', 'audio']
        for field in fields_to_check:
            if field.encode() in body:
                # Find the context
                idx = body.find(field.encode())
                context_start = max(0, idx - 30)
                context_end = min(len(body), idx + 100)
                context = body[context_start:context_end].decode('utf-8', errors='replace')
                print(f"  ✓ '{field}' field found")
                print(f"    Context: {context[:80]}...")
            else:
                print(f"  ✗ '{field}' field NOT found")

        print(f"\nBody size: {len(body)} bytes")
        print(f"\nBody sample (first 500 chars):")
        print("-" * 80)
        print(body_str[:500])
        print("-" * 80)

        # Now try to send it
        print(f"\n{'='*80}")
        print("STEP 3: Sending Request to Spring2")
        print(f"{'='*80}")

        try:
            response = await client.post(url, files=files)

            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Headers:")
            for header, value in response.headers.items():
                if header.lower() in ['content-type', 'content-length']:
                    print(f"  {header}: {value}")

            print(f"\nResponse Body:")
            print("-" * 80)
            print(response.text[:500])
            print("-" * 80)

            if response.status_code in [200, 201]:
                print(f"\n✓ SUCCESS: Spring2 accepted the request")
                try:
                    print(f"Response JSON: {response.json()}")
                except:
                    print(f"(Response is not JSON)")
            else:
                print(f"\n✗ FAILED: Spring2 returned {response.status_code}")

        except asyncio.TimeoutError:
            print(f"\n✗ TIMEOUT: Spring2 not responding")
            print(f"  Check if Spring2 is running on {spring2_url}")

        except httpx.ConnectError as e:
            print(f"\n✗ CONNECTION ERROR: Cannot connect to Spring2")
            print(f"  URL: {spring2_url}")
            print(f"  Error: {e}")

        except Exception as e:
            print(f"\n✗ ERROR: {type(e).__name__}")
            print(f"  {e}")


if __name__ == "__main__":
    asyncio.run(main())