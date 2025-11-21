#!/usr/bin/env python3
"""
Test httpx multipart/form-data encoding for Spring2 API compatibility.

This script verifies that httpx correctly encodes multipart/form-data
requests for the Spring2 save_utterance endpoint.
"""

import asyncio
import httpx
from datetime import datetime, timezone


async def test_multipart_encoding():
    """Test different multipart encoding approaches with httpx"""

    print("=" * 70)
    print("Testing httpx multipart/form-data encoding")
    print("=" * 70)

    # Create dummy data
    session_id = "test-session-123"
    utterance_index = 0
    speaker = "user"
    text = "test utterance text"
    audio_data = b"\x00\x00" * 100  # dummy audio

    # Test 1: Using files parameter with (None, value) tuples for text fields
    print("\n[Test 1] Files parameter with (None, value) tuples for text fields")
    print("-" * 70)

    files = {
        "speaker": (None, speaker),
        "text": (None, text),
        "utterance_index": (None, str(utterance_index)),
        "audio": ("utterance_0.wav", audio_data, "audio/wav"),
    }

    async with httpx.AsyncClient() as client:
        # Create a request without sending it
        request = client.build_request("POST", "http://localhost:8081/internal/sessions/test-session-123/utterances", files=files)

        print(f"Content-Type: {request.headers.get('content-type', 'NOT SET')}")
        print(f"Method: {request.method}")
        print(f"URL: {request.url}")
        print(f"Headers: {dict(request.headers)}")

    # Test 2: Using data parameter for text + files parameter for binary
    print("\n[Test 2] Data parameter for text + Files parameter for binary")
    print("-" * 70)

    data = {
        "speaker": speaker,
        "text": text,
        "utterance_index": str(utterance_index),
    }
    files = {
        "audio": ("utterance_0.wav", audio_data, "audio/wav"),
    }

    async with httpx.AsyncClient() as client:
        request = client.build_request(
            "POST",
            "http://localhost:8081/internal/sessions/test-session-123/utterances",
            data=data,
            files=files,
        )

        print(f"Content-Type: {request.headers.get('content-type', 'NOT SET')}")

    # Test 3: Force multipart by using files for everything (including text fields)
    print("\n[Test 3] Files parameter only with all fields (recommended)")
    print("-" * 70)

    files = {
        "speaker": (None, speaker),
        "text": (None, text),
        "utterance_index": (None, str(utterance_index)),
        "audio": ("utterance_0.wav", audio_data, "audio/wav"),
    }

    async with httpx.AsyncClient() as client:
        request = client.build_request("POST", "http://localhost:8081/internal/sessions/test-session-123/utterances", files=files)

        print(f"Content-Type: {request.headers.get('content-type', 'NOT SET')}")
        print(f"\nContent-Type header indicates multipart: {'multipart' in request.headers.get('content-type', '').lower()}")


if __name__ == "__main__":
    asyncio.run(test_multipart_encoding())