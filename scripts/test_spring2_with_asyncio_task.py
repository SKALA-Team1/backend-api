#!/usr/bin/env python3
"""
Test Spring2 integration using asyncio.create_task() pattern (like in ws_realtime.py).

This tests whether there's an issue with how the save_utterance call is being
scheduled as a background task in the actual WebSocket handler.
"""

import asyncio
import httpx
import sys
import os


async def save_utterance_to_spring2(
    session_id: str,
    speaker: str,
    text: str,
    utterance_index: int,
    audio_data: bytes = None,
):
    """
    Simulate spring2_client.save_utterance() method.
    """
    spring2_url = os.getenv("SPRING2_BASE_URL", "http://localhost:8082").rstrip('/')
    url = f"{spring2_url}/internal/sessions/{session_id}/utterances"

    normalized_speaker = (speaker or "user").lower()
    final_text = text

    files = {
        "speaker": (None, normalized_speaker),
        "text": (None, final_text),
        "utterance_index": (None, str(utterance_index)),
    }

    if audio_data:
        files["audio"] = (f"utterance_{utterance_index}.wav", audio_data, "audio/wav")

    print(f"[save_utterance_to_spring2] Starting request to {url}")
    print(f"  speaker: {normalized_speaker}")
    print(f"  text: {final_text}")
    print(f"  utterance_index: {utterance_index}")
    print(f"  audio: {len(audio_data) if audio_data else 0} bytes")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, files=files)
            response.raise_for_status()

            result = response.json()
            print(f"✓ Utterance saved: {result}")
            return result

    except asyncio.TimeoutError:
        print(f"✗ TIMEOUT: Spring2 not responding")
        return None

    except httpx.ConnectError as e:
        print(f"✗ CONNECTION ERROR: {e}")
        return None

    except httpx.HTTPStatusError as e:
        print(f"✗ HTTP ERROR {e.response.status_code}: {e.response.text}")
        return None

    except Exception as e:
        print(f"✗ ERROR: {type(e).__name__}: {e}")
        return None


async def test_with_create_task():
    """Test using asyncio.create_task() like ws_realtime.py does"""

    print("=" * 80)
    print("Testing Spring2 with asyncio.create_task() pattern")
    print("=" * 80)

    session_id = "test-" + os.urandom(4).hex()
    speaker = "user"
    text = "test from asyncio.create_task()"
    utterance_index = 0
    audio_data = b"\x00\x01" * 500

    print(f"\n[Main] Creating background task for save_utterance...")

    # Schedule as background task (like in ws_realtime.py line 519)
    task = asyncio.create_task(
        save_utterance_to_spring2(
            session_id=session_id,
            speaker=speaker,
            text=text,
            utterance_index=utterance_index,
            audio_data=audio_data,
        )
    )

    print(f"[Main] Task created: {task}")
    print(f"[Main] Continuing without waiting...")

    # In ws_realtime.py, the code doesn't wait for the task to complete
    # It just sends a message to the client immediately
    await asyncio.sleep(0.1)
    print(f"[Main] Sent response to client")

    # Wait for the background task to complete
    print(f"[Main] Waiting for background task...")
    result = await asyncio.wait_for(task, timeout=15.0)
    print(f"[Main] Background task completed with result: {result}")


async def test_with_await():
    """Test using await directly"""

    print("\n" + "=" * 80)
    print("Testing Spring2 with direct await pattern")
    print("=" * 80)

    session_id = "test-" + os.urandom(4).hex()
    speaker = "user"
    text = "test from direct await"
    utterance_index = 0
    audio_data = b"\x00\x01" * 500

    print(f"\n[Main] Awaiting save_utterance...")

    result = await save_utterance_to_spring2(
        session_id=session_id,
        speaker=speaker,
        text=text,
        utterance_index=utterance_index,
        audio_data=audio_data,
    )

    print(f"[Main] Completed with result: {result}")


async def main():
    """Run all tests"""

    # Test 1: asyncio.create_task() pattern
    try:
        await test_with_create_task()
    except asyncio.TimeoutError:
        print(f"\n[ERROR] asyncio.create_task() test timed out")
    except Exception as e:
        print(f"\n[ERROR] asyncio.create_task() test failed: {e}")

    # Test 2: Direct await pattern
    try:
        await test_with_await()
    except asyncio.TimeoutError:
        print(f"\n[ERROR] direct await test timed out")
    except Exception as e:
        print(f"\n[ERROR] direct await test failed: {e}")

    print("\n" + "=" * 80)
    print("Tests completed")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())