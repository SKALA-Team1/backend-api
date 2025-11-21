#!/usr/bin/env python3
"""
Test httpx handling of empty string values in multipart form data.
"""

from httpx._models import Request


def test_empty_fields():
    """Test how httpx handles empty vs missing fields"""

    print("=" * 80)
    print("Testing httpx handling of empty and None values")
    print("=" * 80)

    # Test 1: Empty string
    print("\n[Test 1] Empty string value")
    print("-" * 80)

    files = {
        "text": (None, ""),
        "speaker": (None, "user"),
    }

    req = Request("POST", "http://example.com", files=files)
    body = b""
    for chunk in req.stream:
        body += chunk

    body_str = body.decode('utf-8', errors='replace')
    print(f"Body (first 300 chars):\n{body_str[:300]}")

    if b"text" in body:
        print("✓ Found 'text' field name in body")
        if b"\r\n\r\nuser" in body or b"\r\n\r\n\r\n" in body:
            print("  (appears with empty value)")
    else:
        print("✗ 'text' field name NOT found in body")

    # Test 2: None value (omit field entirely)
    print("\n[Test 2] Omitting field entirely (not using None value)")
    print("-" * 80)

    files2 = {
        "speaker": (None, "user"),
    }

    req2 = Request("POST", "http://example.com", files=files2)
    body2 = b""
    for chunk in req2.stream:
        body2 += chunk

    if b"text" in body2:
        print("✗ 'text' field name found in body (should be omitted)")
    else:
        print("✓ 'text' field name correctly omitted from body")


if __name__ == "__main__":
    test_empty_fields()