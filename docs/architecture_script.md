You are a coding agent working on the SKALA backend.

## High-level goal (서비스 개요)

We are building an English learning service with:
- Real-time role-playing conversations ("roleplaying")
- Textbook-based Q&A sessions ("textbook-based")
- User mypage
- Login / signup / onboarding

The backend is composed of **three servers** and **two data stores**:

1. Spring 1 server: API Gateway + Auth server
2. Spring 2 server: Business/CRUD server
3. FastAPI server: Model serving server
4. PostgreSQL & Qdrant: main data stores (CRUD only from Spring 2, read-only from FastAPI)

You must keep this architecture consistent when generating any code.

---

## 1. Services

### 1-1. Spring 1 server (Gateway + Auth)

Name (example): `spring-gateway`  

Responsibility:
- Entry point for **all** client HTTP requests.
- API Gateway + Authentication/Authorization server.
- Expose `/auth/**` endpoints for login, signup (if needed), token refresh, logout.
- Issue **JWT tokens** (AccessToken / RefreshToken).
- Validate JWT on incoming requests.
- Create **session** for roleplaying / textbook-based sessions:
  - Generate `session_id`
  - Store `session_id` in a shared session store (e.g., Redis) with:
    - userId
    - role
    - scenarioType (ROLEPLAYING / TEXTBOOK)
    - startedAt
    - expiresAt
- Route business-related requests to Spring 2.
- Return WebSocket connection information for roleplaying/textbook sessions (FastAPI endpoint + session_id).

Important constraints:
- Spring 1 is the **source of truth** for:
  - Token issuing
  - Token signing (JWT)
  - Authorization policy (roles, permissions)
- Spring 1 should NOT perform DB CRUD directly on PostgreSQL/Qdrant.

Tech stack:
- Spring Boot 3 (Java 17)
- Spring Security
- JWT (for tokens)
- Optional: Spring Cloud Gateway or custom gateway routing

---

### 1-2. Spring 2 server (Business / CRUD server)

Name (example): `spring-core`  

Responsibility:
- Handle business logic and CRUD for:
  - Mypage
  - Signup / onboarding domain data
  - User profile, levels, job roles, progress, etc.
- Connect to:
  - PostgreSQL (main relational DB)
  - Qdrant (vector DB, e.g. for content/embedding)
- Perform **ALL write operations (CREATE/UPDATE/DELETE)** to PostgreSQL/Qdrant.
- Provide internal APIs for Spring 1:
  - Credential verification (ID/password check) during login.
  - Any user/domain info that Spring 1 needs for authorization decisions.

Auth behavior:
- Does NOT issue tokens.
- Uses JWT that was issued and signed by Spring 1.
- **Option we choose**: Spring 2 directly verifies the JWT signature (JWT distributed verification).
  - Spring 2 knows the public key or shared secret for JWT.
  - Spring 2 extracts userId/role/claims from JWT and uses it for business logic.
- Authorization rules (role, permission meaning) are defined conceptually by Spring 1, but Spring 2 uses the claims inside the JWT to enforce them.

Tech stack:
- Spring Boot 3 (Java 17)
- Spring Data JPA / JDBC for PostgreSQL
- Qdrant Java client
- JWT verification library

---

### 1-3. FastAPI server (Model serving)

Name (example): `fastapi-model-serving`  

Responsibility:
- Serve ML/LLM models for:
  - Real-time roleplaying dialog generation
  - Textbook-based Q&A (pre-defined questions + model answer generation)
- Provide HTTP and WebSocket endpoints:
  - HTTP for internal calls (e.g., from Spring 2 or 1, if needed)
  - WebSocket endpoint for continuous conversation during roleplaying/textbook sessions
- Read data from PostgreSQL/Qdrant as **read-only**:
  - Load user info, textbook content, previous conversation history, etc. to build model input.
- Use `session_id` for authentication/authorization during WebSocket communication.

Auth behavior:
- FastAPI does NOT validate JWT directly.
- FastAPI uses **session_id**:
  - On WebSocket connect:
    - Receives `session_id` as query param or header.
    - Looks up `session_id` in shared session store (Redis).
    - Confirms userId/role/scenarioType are valid and not expired.
  - For each message, relies on the WebSocket connection already having a valid `session_id`.

Tech stack:
- Python 3.x
- FastAPI
- WebSockets
- Redis client (for session lookup)
- PostgreSQL/Qdrant client libraries (read-only usage)

---

## 2. Data stores

### 2-1. PostgreSQL
- Main relational DB for:
  - User accounts
  - Onboarding status
  - Mypage data (profile, statistics, history)
  - Textbook metadata
  - Roleplaying/textbook session logs (if needed)
- CRUD responsibilities:
  - **WRITE**: Only Spring 2 server
  - **READ**: Spring 2 server + FastAPI server (FastAPI is read-only)

### 2-2. Qdrant
- Vector DB for:
  - Embeddings of textbook content, dialogs, etc.
- CRUD responsibilities:
  - **WRITE/UPDATE/DELETE**: Only Spring 2 server
  - **READ**: Spring 2 server + FastAPI server (FastAPI read-only)

---

## 3. Auth & Session flow (very important)

### 3-1. Login

Flow:
1. Client → Spring 1: `/auth/login` with credentials.
2. Spring 1 → Spring 2 (internal API):
   - Verify credential (ID/password) against PostgreSQL.
3. Spring 2:
   - Return verification result and user info to Spring 1.
4. Spring 1:
   - If successful, issue JWT (AccessToken + RefreshToken).
   - Send tokens to client.

Requirements:
- Spring 1 signs the JWT.
- Spring 2 has the key to verify signature but does not issue tokens.

---

### 3-2. Normal web domain (mypage, onboarding, etc.)

Flow:
1. Client → Spring 1:
   - Sends HTTP request with `Authorization: Bearer <AccessToken>`.
2. Spring 1:
   - Validates JWT (signature, expiration, etc).
   - Routes the request to Spring 2 (e.g. `/mypage/**`).
3. Spring 2:
   - Option A: trust the already-validated token and rely on headers/attributes provided by Spring 1.
   - Option B (preferred for our script): re-validate the JWT signature locally to extract userId/role.
   - Execute business logic and CRUD on PostgreSQL/Qdrant.
   - Return result back through Spring 1 to client.

---

### 3-3. Start roleplaying/textbook session

Flow:
1. Client (already logged in) → Spring 1:
   - `POST /roleplaying/sessions` or `POST /textbook-sessions`
   - Includes `Authorization: Bearer <AccessToken>`.
2. Spring 1:
   - Validate JWT again (normal protected endpoint).
   - Check authorization (is this user allowed to start this type of session?).
   - Generate a new `session_id`.
   - Store the session in Redis (or similar) as:
     - key: session_id
     - value: { userId, role, scenarioType, startedAt, expiresAt }
3. Spring 1:
   - Return response to client with:
     - `session_id`
     - WebSocket endpoint URL for FastAPI (e.g., `wss://fastapi-server/roleplaying`).

---

### 3-4. WebSocket communication for roleplaying/textbook

Flow:
1. Client connects to FastAPI via WebSocket:
   - `wss://fastapi-server/roleplaying?session_id=<session_id>`
2. FastAPI:
   - On connection, reads `session_id`.
   - Looks up `session_id` in Redis.
   - If valid, accept connection and associate WebSocket with that user/session.
3. During the session:
   - Client sends messages over WebSocket.
   - FastAPI:
     - Uses session info (userId, scenarioType) and reads any needed data from PostgreSQL/Qdrant (read-only).
     - Calls model/LLM to generate responses.
     - Sends responses back over WebSocket.
4. On session end:
   - Client sends a "finish" message OR timeout occurs.
   - FastAPI or Spring 1:
     - Clear `session_id` from Redis.
     - Close WebSocket connection.

Important:
- During WebSocket session, we do NOT verify JWT on each message.
- We rely on the `session_id` that was created after a valid authenticated start request.

---

## 4. Non-functional requirements

- All writes to PostgreSQL/Qdrant must go through **Spring 2**.
- FastAPI must only perform read operations on databases.
- Auth and token signing logic must be centralized in **Spring 1**.
- For session storage, assume Redis (or similar in-memory store) is available and shared between Spring 1 and FastAPI.

---

## 5. What you should generate or maintain

When I ask you to generate code or project structure, you must follow:

- Keep three separate services:
  - `spring-gateway` (Spring 1)
  - `spring-core` (Spring 2)
  - `fastapi-model-serving` (FastAPI)
- Use clear package/module separation according to these responsibilities.
- Use JWT for auth between client and Spring servers.
- Use `session_id` for WebSocket auth between client and FastAPI.
- Ensure Spring 2 and FastAPI do not violate the read/write constraints on the databases.

If I ask for:
- Directory structure → reflect this architecture.
- API spec → ensure routing and responsibility separation follow this design.
- Code examples → respect the auth/session flow and DB constraints described above.