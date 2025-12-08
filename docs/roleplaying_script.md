You are Claude Code, a coding agent working on the SKALA backend.

Your job is to generate code, directory structures, and API definitions that strictly follow the service architecture described below.

======================================================================
[HIGH-LEVEL SERVICE OVERVIEW]
======================================================================

We are building an English learning service with:

- Real-time roleplaying English conversation ("roleplaying")
- Mypage
- Login / signup / onboarding

The backend has **three servers** and **multiple data stores**:

1) Spring 1 server  = API Gateway + Auth server
2) Spring 2 server  = Business/CRUD + S3/DB write server
3) FastAPI server   = Model serving + real-time STT/LLM

Data stores:

- PostgreSQL  (relational DB)
- Qdrant      (vector DB)
- S3          (audio file storage)
- Redis       (session storage for `session_id`)

You MUST keep this architecture consistent whenever you generate any code or APIs.

======================================================================
[SERVER RESPONSIBILITIES]
======================================================================

-------------------------
1. Spring 1 (Gateway/Auth)
-------------------------
- Acts as the **single entry point** for all client HTTP requests.
- Responsibilities:
  - Login, logout, token issuing (JWT Access/Refresh)
  - JWT validation on incoming requests
  - Authorization decisions (based on roles, user status)
  - Session creation for roleplaying:
    - Generate `session_id`
    - Store `session_id` in Redis:
      - `session_id -> { userId, role, scenarioType, startedAt, expiresAt }`
  - Route business-related HTTP requests to Spring 2
  - Provide WebSocket endpoint info (FastAPI URL + `session_id`) to the client

- Important constraints:
  - Spring 1 is the **source of truth** for:
    - JWT signing
    - Auth & authorization policies
  - Spring 1 does NOT perform CRUD on PostgreSQL/Qdrant itself.

-------------------------
2. Spring 2 (Business/CRUD/S3 write)
-------------------------
- Handles business logic for:
  - Mypage
  - Signup / onboarding data
  - User profile, progress, etc.
- Responsibilities:
  - **All WRITE operations (CREATE/UPDATE/DELETE)** to:
    - PostgreSQL
    - Qdrant
    - S3 (audio file uploads)
  - Provide internal APIs for Spring 1:
    - Credential verification for login (ID/password check)
  - Provide internal APIs for FastAPI:
    - Receive audio data (utterances) and store them:
      - Upload audio to S3
      - Insert utterance metadata into PostgreSQL

- Auth behavior:
  - Does NOT issue tokens.
  - Trusts JWT signed by Spring 1.
  - Uses a shared secret or public key to verify JWT signature if needed.
  - Extracts `userId`, `role`, etc. from JWT for authorization inside Spring 2.

-------------------------
3. FastAPI (Model Serving + Real-Time STT/LLM)
-------------------------
- Handles real-time model serving for:
  - Roleplaying dialog generation
- Responsibilities:
  - WebSocket server for real-time communication with the client.
  - Generate AI tutor questions/responses (LLM calls).
  - Perform STT (speech-to-text) on incoming user audio:
    - Audio is streamed from the client to FastAPI via WebSocket.
    - FastAPI uses an STT engine (internal model or external API).
    - Partial and final transcripts are sent back to the client in real time.
  - Forward final utterances (audio + STT text) to Spring 2 over internal APIs
    for persistence.

- **Critical constraint:**
  - FastAPI is **READ-ONLY** for all persistent stores:
    - No WRITE to PostgreSQL
    - No WRITE to Qdrant
    - No WRITE to S3
  - All writes MUST go through Spring 2. FastAPI may only READ from DBs/S3 and send data to Spring 2 for storage.

- Data access:
  - FastAPI can read from:
    - PostgreSQL (session/utterance data, user info)
    - Qdrant (for retrieval-based prompts)
    - S3 (if needed to re-load audio)
  - All DB & S3 writes are delegated to Spring 2 via internal HTTP APIs.

======================================================================
[DATA STORES]
======================================================================

- PostgreSQL
  - Stores:
    - session metadata
    - utterance records
    - evaluation results
    - user profile & onboarding data
  - Spring 2 = full CRUD
  - FastAPI = READ-ONLY

- Qdrant
  - Stores:
    - dialog-related embeddings
  - Spring 2 = write/update/delete
  - FastAPI = READ-ONLY

- S3
  - Stores:
    - All audio files from user utterances
  - Spring 2:
    - Has write permissions
    - Performs uploads
  - FastAPI:
    - Has no write permission
    - May read if necessary

- Redis
  - Stores:
    - `session_id -> user/session info`
  - Spring 1:
    - Creates session entries
  - FastAPI:
    - Reads to validate incoming WebSocket connections

======================================================================
[ROLEPLAYING SESSION FLOW - END-TO-END]
======================================================================

1) Login
--------
1. Client → Spring 1: `/auth/login` with credentials.
2. Spring 1 → Spring 2: internal API to verify credentials against PostgreSQL.
3. Spring 2 → Spring 1: result + user data.
4. Spring 1 → Client: JWT AccessToken + RefreshToken.

2) Start Roleplaying Session
----------------------------
1. Client → Spring 1:
   - `POST /roleplaying/sessions` with `Authorization: Bearer <AccessToken>`.
2. Spring 1:
   - Validates JWT.
   - Checks if this user is allowed to start a session.
   - Generates a new `session_id`.
   - Stores `session_id` in Redis with user info & scenario type.
3. Spring 1 → Client:
   - Returns `session_id`.
   - Returns FastAPI WebSocket endpoint:
     - e.g. `wss://fastapi-server/roleplaying?session_id=<session_id>`.

3) WebSocket Connection (Client ↔ FastAPI)
------------------------------------------
1. Client opens WebSocket to FastAPI:
   - `wss://fastapi-server/roleplaying?session_id=...`
2. FastAPI:
   - Reads `session_id`.
   - Validates it via Redis.
   - On success: accepts connection and associates that WebSocket with the session.

4) AI Question → TTS/Avatar
---------------------------
1. FastAPI:
   - Computes the next AI tutor question (using LLM, retrieval, etc.).
   - Sends a message to the client:
     - `{ "type": "ai_text", "text": "..." }`
2. Client:
   - Uses TTS API to generate audio from `ai_text`.
   - Uses Avatar API to render the talking avatar.
   - Plays the audio and animation to the user.

5) User Utterance (Audio Stream → STT → Text)
---------------------------------------------
**This is the critical real-time part.**

- Requirement:
  - STT result should appear on the UI almost in real-time.
  - Frontend should not be heavily loaded by STT computation.
  - Therefore, STT is performed on the server (FastAPI).

Flow:

1. Client:
   - Captures user microphone audio.
   - Streams audio chunks to FastAPI via WebSocket:
     - `{ "type": "audio_chunk", "chunk": <binary> }`
2. FastAPI:
   - For each audio chunk:
     - Feeds it into the STT engine (streaming mode if possible).
     - When partial transcript is available:
       - Sends partial text back:
         - `{ "type": "stt_partial", "text": "I work as..." }`
   - When the utterance ends (e.g., client sends `utterance_end` message):
     - Finalizes STT result:
       - e.g. `"I work as a software engineer."`
     - Sends final transcript to client:
       - `{ "type": "stt_final", "text": "I work as a software engineer." }`
     - Aggregates the full audio for this utterance and its final STT text.

3. FastAPI → Spring 2 (internal API):
   - Sends the utterance audio + metadata for persistence:
     - `POST /internal/sessions/{session_id}/utterances`
     - Body example:
       ```json
       {
         "audio_blob": "<binary or base64>",
         "stt_text": "I work as a software engineer.",
         "utterance_index": 3,
         "started_at": "...",
         "ended_at": "..."
       }
       ```

4. Spring 2:
   - Uploads the audio to S3:
     - Path example: `s3://skala/sessions/{session_id}/utterance_{n}.wav`
   - Inserts a row into PostgreSQL utterance table with:
     - session_id
     - s3_url
     - stt_text
     - utterance_index
     - timestamps

5. FastAPI:
   - Optionally notifies client that the utterance was stored:
     - `{ "type": "utterance_saved", "index": 3 }`

**Important**: FastAPI must not directly write to S3 or DB.
It only forwards audio/metadata to Spring 2.

6) Session End & Evaluation
---------------------------
1. Client → Spring 1 → Spring 2:
   - `POST /roleplaying/sessions/{session_id}/finish`
2. Spring 2:
   - Marks the session as finished in PostgreSQL.
   - Triggers evaluation by calling FastAPI internal endpoint:
     - `POST /internal/sessions/{session_id}/evaluate`
3. FastAPI (evaluation step):
   - Reads all utterances for the session from PostgreSQL (read-only).
   - Optionally reads audio from S3 (read-only).
   - Computes:
     - Per-utterance evaluation:
       - Pronunciation, fluency, grammar, expression, etc.
     - Overall session evaluation:
       - Scores & feedback text.
   - Sends results back to Spring 2:
     - `POST /internal/sessions/{session_id}/evaluation-result`
4. Spring 2:
   - Stores evaluation results in PostgreSQL evaluation table.

======================================================================
[DATA MODEL HINTS]
======================================================================

You may assume schemas like:

- `session` table:
  - id (session_id)
  - user_id
  - type (ROLEPLAYING)
  - started_at, ended_at, ...

- `utterance` table:
  - id
  - session_id
  - index
  - speaker (USER/AI)
  - s3_url
  - stt_text
  - started_at, ended_at

- `evaluation` table:
  - id
  - session_id
  - overall_score
  - overall_feedback
  - per_utterance JSON
  - created_at

======================================================================
[WHAT YOU MUST RESPECT WHEN GENERATING CODE]
======================================================================

Whenever you generate code, you MUST:

1. Preserve server boundaries:
   - Do NOT give FastAPI any direct write operation to PostgreSQL, Qdrant, or S3.
   - All writes go through Spring 2.
2. Keep auth responsibilities in Spring 1:
   - All client HTTP calls must conceptually go through Spring 1.
   - JWT is issued and validated by Spring 1.
3. Implement real-time roleplaying as:
   - Client ↔ FastAPI via WebSocket for audio/text streaming.
   - FastAPI ↔ Spring 2 via internal HTTP APIs for persistence and evaluations.
4. Minimize frontend burden:
   - STT MUST be done on the server side (FastAPI).
   - Client only captures audio, sends to FastAPI, and displays returned text.
5. Follow separation of concerns:
   - Spring 1 = Auth & Gateway
   - Spring 2 = Business logic + DB/S3 writes
   - FastAPI = LLM/STT + real-time orchestration (read-only to persistent stores)

If the user asks for:
- Directory structures → reflect the three separate services and their roles.
- API definitions → respect the flows and boundaries above.
- Sample implementations → do not break the read-only constraint of FastAPI and write-only responsibility of Spring 2.

======================================================================
End of SKALA Roleplaying Architecture Description.
======================================================================