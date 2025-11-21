# Spring2 Integration Fixes

## Problem Summary

The Spring2 API was returning error: `Required part 'text' is not present` when FastAPI attempted to send multipart form-data requests to save utterances.

Error symptoms:
- HTTP 415 Unsupported Media Type with `Content-Type: application/octet-stream`
- HTTP 415 with `Content-Type: application/x-www-form-urlencoded`
- MissingServletRequestPartException for required form field 'text'

## Root Causes Identified

1. **Multipart Encoding Issue**: httpx's behavior depends on parameter usage:
   - Using only `data` parameter → sends `application/x-www-form-urlencoded`
   - Using `files` parameter → sends `multipart/form-data` ✓
   - Mixing `data` + `files` → can still result in form-urlencoded

2. **Missing Parameters in WebSocket Handler**: The ws_realtime.py was missing required parameters when calling save_utterance()

## Fixes Applied

### 1. Fixed spring2_client.py save_utterance() (Lines 116-139)

**Before:**
```python
data = {
    "speaker": normalized_speaker,
    "text": final_text,
    "utterance_index": str(utterance_index),
}
files = {}
if audio_data:
    files["audio"] = (...)

if files:
    response = await client.post(url, data=data, files=files)
else:
    response = await client.post(url, data=data)
```

**After:**
```python
files = {
    "speaker": (None, normalized_speaker),
    "text": (None, final_text),
    "utterance_index": (None, str(utterance_index)),
}

if started_at:
    files["started_at"] = (None, _to_offset(started_at))
if ended_at:
    files["ended_at"] = (None, _to_offset(ended_at))

if audio_data:
    files["audio"] = (f"utterance_{utterance_index}.wav", audio_data, "audio/wav")

response = await client.post(url, files=files)
```

**Why this works:**
- All fields are in the `files` parameter as `(None, value)` tuples
- The `None` first element indicates "no filename" (i.e., form field, not a file)
- httpx only uses multipart/form-data when `files` parameter is present
- This approach ensures all required fields are transmitted correctly

### 2. Fixed ws_realtime.py (Line 519-526)

Added missing parameters to save_utterance() call:
- `speaker="user"` (was missing)
- `text=stt_text` (was missing)

## Verification

Created comprehensive diagnostic scripts to verify the fix:

### Test Files Created

1. **scripts/test_httpx_multipart.py**
   - Tests different multipart encoding approaches
   - Verifies Content-Type is set correctly

2. **scripts/test_httpx_direct.py**
   - Inspects actual request body content
   - Verifies field names are present: `text`, `speaker`, `utterance_index`, `audio`

3. **scripts/test_empty_fields.py**
   - Tests how httpx handles empty string values
   - Confirms empty values are included in multipart body

4. **scripts/diagnose_spring2_issue.py**
   - Comprehensive diagnostic tool
   - Shows exact request being sent to Spring2
   - Helps identify if Spring2 is receiving requests correctly

5. **scripts/test_spring2_with_asyncio_task.py**
   - Tests both `asyncio.create_task()` and `await` patterns
   - Helps diagnose issues with background task scheduling

### Test Results

```
Content-Type: multipart/form-data; boundary=<UUID>

Field Presence:
✓ Found 'speaker' field name in body
✓ Found 'text' field name in body
✓ Found 'utterance_index' field name in body
✓ Found 'audio' field name in body (when provided)

Empty String Handling:
✓ Empty 'text' field is correctly included in multipart body
```

## Request Format Example

When calling save_utterance(), the HTTP request body looks like:

```
--<boundary>
Content-Disposition: form-data; name="speaker"

user
--<boundary>
Content-Disposition: form-data; name="text"

hello world
--<boundary>
Content-Disposition: form-data; name="utterance_index"

0
--<boundary>
Content-Disposition: form-data; name="audio"; filename="utterance_0.wav"
Content-Type: audio/wav

<binary audio data>
--<boundary>--
```

## HTTPx Multipart Encoding Rules

- **Use `files` parameter** for multipart/form-data
- **Use `data` parameter alone** for application/x-www-form-urlencoded
- **Use `files` for text fields** with `(None, value)` tuples
- **Use `files` for binary fields** with `(filename, content, content_type)` tuples
- **Empty strings are preserved** in multipart encoding
- **Only include `files` parameter** in the request for correct Content-Type

## Testing Instructions

To verify the Spring2 integration works:

```bash
# Start Spring2 on port 8082
# Set environment variable
export SPRING2_BASE_URL=http://localhost:8082

# Run diagnostic
python scripts/diagnose_spring2_issue.py

# Run with asyncio task pattern
python scripts/test_spring2_with_asyncio_task.py

# Run voice test to trigger save_utterance calls
python scripts/test_voice_client.py
```

## Related Files

- `app/integrations/clients/spring2_client.py` - Spring2 HTTP client
- `app/roleplaying/ws_realtime.py` - WebSocket handler that calls save_utterance()
- `app/roleplaying/ws_models.py` - WebSocket message models

## Notes

1. The httpx AsyncClient is reused globally via `spring2_client` instance
2. The client uses lazy initialization via `_get_client()` method
3. Timeout is set to 30 seconds for all requests
4. Error logging includes response status code and error message
5. The save_utterance() call in ws_realtime.py uses `asyncio.create_task()` to run in background