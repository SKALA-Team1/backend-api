#!/usr/bin/env python3
"""
Direct test of httpx multipart encoding using httpx internals.
"""

from httpx._content import encode_request
from httpx._models import Request


def test_multipart_direct():
    """Test multipart encoding directly"""

    print("=" * 80)
    print("Direct httpx multipart encoding inspection")
    print("=" * 80)

    # Create dummy data
    speaker = "user"
    text = "test utterance text"
    utterance_index = 0
    audio_data = b"AUDIO_DATA" * 10

    # Test: Using files parameter with (None, value) tuples
    print("\n[Current Implementation] Files with (None, value) tuples")
    print("-" * 80)

    files = {
        "speaker": (None, speaker),
        "text": (None, text),
        "utterance_index": (None, str(utterance_index)),
        "audio": ("utterance_0.wav", audio_data, "audio/wav"),
    }

    req = Request(
        "POST",
        "http://localhost:8081/internal/sessions/test-session-123/utterances",
        files=files,
    )

    print(f"Content-Type: {req.headers.get('content-type')}")
    print(f"Method: {req.method}")

    # Check the request body
    print(f"\nInspecting request content:")

    # The request body is a stream, but we can check what encoding is used
    if hasattr(req, '_content'):
        print(f"Has _content attribute: {req._content}")

    # Let's look at the stream
    if hasattr(req, 'stream'):
        stream = req.stream
        print(f"Stream type: {type(stream)}")

        # Try to consume the stream
        if hasattr(stream, '__iter__'):
            print(f"\nStream content (iterating):")
            total_size = 0
            full_content = b""
            for i, chunk in enumerate(stream):
                total_size += len(chunk)
                full_content += chunk

            print(f"Total size: {total_size} bytes")

            # Print decoded content
            content_str = full_content.decode('utf-8', errors='replace')
            print(f"\nFull request body (first 1000 chars):\n{content_str[:1000]}")

            # Check for field names
            print(f"\n[Field name checks]")
            if b"text" in full_content:
                print("✓ Found 'text' field name in body")
            else:
                print("✗ 'text' field name NOT found in body")

            if b"speaker" in full_content:
                print("✓ Found 'speaker' field name in body")
            else:
                print("✗ 'speaker' field name NOT found in body")

            if b"utterance_index" in full_content:
                print("✓ Found 'utterance_index' field name in body")
            else:
                print("✗ 'utterance_index' field name NOT found in body")

    # Now test with alternative approach - using data + files
    print("\n\n[Alternative] Data parameter + Files parameter")
    print("-" * 80)

    data = {
        "speaker": speaker,
        "text": text,
        "utterance_index": str(utterance_index),
    }
    files_alt = {
        "audio": ("utterance_0.wav", audio_data, "audio/wav"),
    }

    req_alt = Request(
        "POST",
        "http://localhost:8081/internal/sessions/test-session-123/utterances",
        data=data,
        files=files_alt,
    )

    print(f"Content-Type: {req_alt.headers.get('content-type')}")

    if hasattr(req_alt, 'stream'):
        stream_alt = req_alt.stream
        if hasattr(stream_alt, '__iter__'):
            for i, chunk in enumerate(stream_alt):
                if i == 0:
                    chunk_str = chunk.decode('utf-8', errors='replace')
                    print(f"First chunk ({len(chunk)} bytes):\n{chunk_str[:500]}")
                    if b"text" in chunk:
                        print("✓ Found 'text' field in first chunk")


if __name__ == "__main__":
    test_multipart_direct()