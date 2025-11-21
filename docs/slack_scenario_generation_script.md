You are Claude Code, a coding agent working on the SKALA FastAPI server.

Your job is to implement the Slack conversation analysis and scenario generation feature that integrates with the Spring 2 backend.

======================================================================
[OVERVIEW - SLACK SCENARIO GENERATION FLOW]
======================================================================

The system generates English conversation practice scenarios from users' Slack conversation history.

Key concept:
- User selects a specific date (e.g., "2025-01-15")
- System retrieves ALL Slack messages from that date
- FastAPI analyzes the conversation context using LLM
- FastAPI generates MULTIPLE scenarios (6 scenarios total):
  - 3 AI roles: "Project Manager", "Tech Lead", "QA Engineer"
  - 2 topic types per role: "overview", "detail"
- Spring 2 saves all results to MySQL database

======================================================================
[ARCHITECTURE CONSTRAINTS]
======================================================================

CRITICAL RULES (from roleplaying_script.md):

1. FastAPI = READ-ONLY for persistent storage
   - NO WRITE to PostgreSQL/MySQL
   - NO WRITE to Qdrant
   - NO WRITE to S3
   - All writes go through Spring 2

2. FastAPI responsibilities:
   - LLM-based analysis and generation
   - Real-time STT/TTS during sessions
   - Read from databases for context
   - Send results to Spring 2 for persistence

3. Spring 2 responsibilities:
   - ALL database writes (CREATE/UPDATE/DELETE)
   - Store analysis results from FastAPI
   - Manage Subject and Scenario entities

======================================================================
[API SPECIFICATION - WHAT YOU NEED TO IMPLEMENT]
======================================================================

Endpoint to implement in FastAPI:
```
POST /internal/scenarios/analyze-conversation
```

This endpoint is called by Spring 2 when user requests scenario generation from Slack messages.

----------------------------
REQUEST from Spring 2:
----------------------------

```json
{
  "userId": 456,
  "conversationDate": "2025-01-15",
  "messages": [
    {
      "timestamp": "2025-01-15T09:00:00",
      "senderName": "John",
      "text": "We need to refactor the auth module"
    },
    {
      "timestamp": "2025-01-15T10:30:00",
      "senderName": "Sarah",
      "text": "The JWT token expiration is too short"
    },
    {
      "timestamp": "2025-01-15T11:00:00",
      "senderName": "John",
      "text": "Let's also improve the refresh token logic"
    },
    {
      "timestamp": "2025-01-15T14:00:00",
      "senderName": "Sarah",
      "text": "Should we include this in the current sprint?"
    },
    {
      "timestamp": "2025-01-15T15:00:00",
      "senderName": "John",
      "text": "Yes, let's start with the design document"
    }
  ],
  "aiRoles": [
    "Project Manager",
    "Tech Lead",
    "QA Engineer"
  ]
}
```

**Fields:**
- `userId`: ID of the user who owns these messages
- `conversationDate`: Date of the conversation (LocalDate format)
- `messages`: List of Slack messages from that entire day
  - `timestamp`: When the message was sent (ISO 8601 format)
  - `senderName`: Name of the person who sent the message
  - `text`: Content of the message
- `aiRoles`: Fixed list of AI roles to generate scenarios for (always these 3 roles)

----------------------------
RESPONSE to Spring 2:
----------------------------

```json
{
  "subject": {
    "myRole": "Junior Developer",
    "situation": "Discussing authentication module refactoring priorities and implementation plan",
    "conversationDate": "2025-01-15",
    "messageCount": 15
  },
  "scenarios": [
    {
      "aiRole": "Project Manager",
      "topicType": "overview",
      "title": "Auth Refactoring - Project Planning",
      "fixedQuestions": [
        "What's the main motivation for this refactoring?",
        "How will this impact our current sprint timeline?",
        "What are the key deliverables you're planning?"
      ]
    },
    {
      "aiRole": "Project Manager",
      "topicType": "detail",
      "title": "Sprint Planning and Resource Allocation",
      "fixedQuestions": [
        "How many story points do you estimate for this work?",
        "Which team members should be involved?",
        "What are the potential risks we should plan for?"
      ]
    },
    {
      "aiRole": "Tech Lead",
      "topicType": "overview",
      "title": "Auth Architecture Discussion",
      "fixedQuestions": [
        "What's wrong with the current authentication architecture?",
        "Which design pattern do you recommend?",
        "How does this fit into our microservices architecture?"
      ]
    },
    {
      "aiRole": "Tech Lead",
      "topicType": "detail",
      "title": "JWT Implementation Deep Dive",
      "fixedQuestions": [
        "Explain the difference between access tokens and refresh tokens",
        "How should we handle token rotation?",
        "What's your approach to securing token storage?"
      ]
    },
    {
      "aiRole": "QA Engineer",
      "topicType": "overview",
      "title": "Auth Testing Strategy",
      "fixedQuestions": [
        "What are the main security concerns we should test?",
        "How will you verify the authentication flow?",
        "What edge cases should we consider?"
      ]
    },
    {
      "aiRole": "QA Engineer",
      "topicType": "detail",
      "title": "Security Testing and Penetration Testing",
      "fixedQuestions": [
        "How do we test for token hijacking vulnerabilities?",
        "What tools do you recommend for security testing?",
        "Can you explain your approach to testing session management?"
      ]
    }
  ]
}
```

**Response Structure:**

`subject` object:
- `myRole` (string): The user's role inferred from conversation (e.g., "Junior Developer", "Product Manager", "DevOps Engineer")
- `situation` (string): Brief description of what the conversation was about (1-2 sentences)
- `conversationDate` (date): Same as request (for validation)
- `messageCount` (integer): Same as request (for validation)

`scenarios` array (MUST contain exactly 6 scenarios):
- `aiRole` (string): One of "Project Manager", "Tech Lead", or "QA Engineer"
- `topicType` (string): Either "overview" or "detail"
  - "overview": High-level, general discussion about the topic
  - "detail": Deep dive into specific technical/professional aspects
- `title` (string): Descriptive title for the scenario (max 200 chars)
- `fixedQuestions` (array of strings): 3-5 questions the AI tutor will ask during the conversation practice
  - Questions should be relevant to the scenario topic
  - Questions should be appropriate for the AI role (PM asks about planning, Tech Lead asks about architecture, QA asks about testing)
  - Questions should encourage the user to practice professional English conversation

======================================================================
[LLM PROMPT DESIGN GUIDELINES]
======================================================================

When implementing this endpoint, you'll need to call an LLM (e.g., OpenAI GPT, Claude) to analyze the conversation.

Recommended prompt structure:

----------------------------
Step 1: Analyze conversation context
----------------------------

Prompt to LLM:
```
You are analyzing a Slack conversation to help a non-native English speaker practice professional English.

Conversation date: {conversationDate}
Messages:
{format all messages with timestamp, sender, and text}

Based on this conversation, determine:
1. What role is the user likely playing? (e.g., "Junior Developer", "Product Manager", "Designer")
2. What is the main topic/situation being discussed? (1-2 sentences)

Respond in JSON format:
{
  "myRole": "...",
  "situation": "..."
}
```

----------------------------
Step 2: Generate scenarios for each AI role
----------------------------

For EACH AI role ("Project Manager", "Tech Lead", "QA Engineer"):
For EACH topic type ("overview", "detail"):

Prompt to LLM:
```
You are creating an English conversation practice scenario based on this Slack conversation:

Conversation topic: {situation}
User's role: {myRole}

Create a scenario where the user practices talking to a {aiRole} about this topic.

Topic type: {topicType}
- If "overview": Create a high-level, general discussion scenario
- If "detail": Create a deep-dive, technical/detailed discussion scenario

Generate:
1. A descriptive title for this scenario (max 200 characters)
2. 3-5 questions that the {aiRole} would ask the user during this conversation

The questions should:
- Be relevant to the original Slack conversation topic
- Match the perspective of a {aiRole}
- Be appropriate for the {topicType} (overview = broad, detail = specific)
- Help the user practice professional English conversation skills

Respond in JSON format:
{
  "title": "...",
  "fixedQuestions": ["...", "...", "..."]
}
```

----------------------------
Step 3: Combine results
----------------------------

Combine the results from Step 1 and Step 2 into the final response format shown above.

======================================================================
[IMPLEMENTATION REQUIREMENTS]
======================================================================

1. **Error Handling**
   - If messages array is empty: return 400 Bad Request
   - If LLM call fails: return 500 Internal Server Error with error details
   - If conversation is too vague to analyze: still generate generic scenarios

2. **Performance**
   - LLM calls can be expensive and slow
   - Consider making parallel LLM calls for the 6 scenarios (if your LLM provider supports it)
   - Spring 2 has set a 60-second timeout, so respond within 60 seconds

3. **LLM Model Selection**
   - Use a strong model for conversation analysis (e.g., GPT-4, Claude Sonnet)
   - Scenario generation can use a faster model if needed (e.g., GPT-3.5-turbo)

4. **Consistency**
   - ALL 6 scenarios must be generated (3 roles × 2 types)
   - Each scenario must have 3-5 fixed questions
   - Titles should be descriptive and professional

5. **Data Flow**
   - FastAPI does NOT save anything to database
   - FastAPI only performs LLM analysis and returns results
   - Spring 2 will handle all database writes

======================================================================
[EXAMPLE CONVERSATION SCENARIOS]
======================================================================

Example 1: Technical Discussion
Slack conversation about "database migration issues"
→ User role: "Backend Developer"
→ Scenarios:
  - Project Manager (overview): "Database Migration Project Planning"
  - Project Manager (detail): "Risk Assessment and Timeline Planning"
  - Tech Lead (overview): "Database Architecture and Migration Strategy"
  - Tech Lead (detail): "Zero-Downtime Migration Implementation"
  - QA Engineer (overview): "Data Integrity Testing Strategy"
  - QA Engineer (detail): "Migration Rollback and Recovery Testing"

Example 2: Product Discussion
Slack conversation about "new user onboarding feature"
→ User role: "Product Designer"
→ Scenarios:
  - Project Manager (overview): "Feature Prioritization and Roadmap"
  - Project Manager (detail): "User Story Definition and Acceptance Criteria"
  - Tech Lead (overview): "Technical Feasibility and Architecture"
  - Tech Lead (detail): "API Design and Data Flow"
  - QA Engineer (overview): "User Experience Testing Plan"
  - QA Engineer (detail): "A/B Testing and Metrics Validation"

Example 3: Operations Discussion
Slack conversation about "server downtime incident"
→ User role: "DevOps Engineer"
→ Scenarios:
  - Project Manager (overview): "Incident Communication and Stakeholder Management"
  - Project Manager (detail): "Post-Mortem and Action Items"
  - Tech Lead (overview): "Root Cause Analysis Discussion"
  - Tech Lead (detail): "Infrastructure Improvements and Prevention"
  - QA Engineer (overview): "Monitoring and Alert System Review"
  - QA Engineer (detail): "Disaster Recovery Testing Procedures"

======================================================================
[TESTING]
======================================================================

To test your implementation:

1. Start FastAPI server on port 8000
2. Use curl or Postman to send a test request:

```bash
curl -X POST http://localhost:8000/internal/scenarios/analyze-conversation \
  -H "Content-Type: application/json" \
  -d '{
    "userId": 1,
    "conversationDate": "2025-01-15",
    "messages": [
      {"timestamp": "2025-01-15T09:00:00", "senderName": "Alice", "text": "The login page is too slow"},
      {"timestamp": "2025-01-15T09:15:00", "senderName": "Bob", "text": "We should add caching"},
      {"timestamp": "2025-01-15T09:30:00", "senderName": "Alice", "text": "Good idea, what about Redis?"}
    ],
    "aiRoles": ["Project Manager", "Tech Lead", "QA Engineer"]
  }'
```

3. Verify the response contains:
   - `subject` with `myRole` and `situation`
   - `scenarios` array with exactly 6 items
   - Each scenario has `aiRole`, `topicType`, `title`, and `fixedQuestions`

======================================================================
[CODE STRUCTURE RECOMMENDATIONS]
======================================================================

Suggested file structure for FastAPI:

```
fastapi_server/
├── app/
│   ├── routers/
│   │   └── internal_scenarios.py  # PUT THE NEW ENDPOINT HERE
│   ├── services/
│   │   ├── llm_service.py         # LLM calling logic
│   │   └── scenario_service.py    # Scenario generation business logic
│   ├── models/
│   │   ├── requests.py            # Pydantic models for request
│   │   └── responses.py           # Pydantic models for response
│   └── main.py
```

Suggested implementation:

```python
# models/requests.py
from pydantic import BaseModel
from datetime import date, datetime
from typing import List

class SlackMessageDto(BaseModel):
    timestamp: datetime
    senderName: str
    text: str

class AnalysisRequestDto(BaseModel):
    userId: int
    conversationDate: date
    messages: List[SlackMessageDto]
    aiRoles: List[str]

# models/responses.py
class SubjectInfoDto(BaseModel):
    myRole: str
    situation: str
    conversationDate: date
    messageCount: int

class ScenarioInfoDto(BaseModel):
    aiRole: str
    topicType: str
    title: str
    fixedQuestions: List[str]

class AnalysisResultDto(BaseModel):
    subject: SubjectInfoDto
    scenarios: List[ScenarioInfoDto]

# routers/internal_scenarios.py
from fastapi import APIRouter, HTTPException
from app.models.requests import AnalysisRequestDto
from app.models.responses import AnalysisResultDto
from app.services.scenario_service import ScenarioService

router = APIRouter(prefix="/internal/scenarios", tags=["internal"])

@router.post("/analyze-conversation", response_model=AnalysisResultDto)
async def analyze_conversation(request: AnalysisRequestDto):
    """
    Analyze Slack conversation and generate multiple scenarios
    Called by Spring 2 server
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    service = ScenarioService()
    result = await service.analyze_and_generate(request)
    return result

# services/scenario_service.py
class ScenarioService:
    async def analyze_and_generate(self, request: AnalysisRequestDto) -> AnalysisResultDto:
        # Step 1: Analyze conversation context
        subject_info = await self._analyze_conversation_context(request.messages)

        # Step 2: Generate scenarios for each AI role and topic type
        scenarios = []
        for ai_role in request.aiRoles:
            for topic_type in ["overview", "detail"]:
                scenario = await self._generate_scenario(
                    messages=request.messages,
                    my_role=subject_info["myRole"],
                    situation=subject_info["situation"],
                    ai_role=ai_role,
                    topic_type=topic_type
                )
                scenarios.append(scenario)

        # Step 3: Build response
        return AnalysisResultDto(
            subject=SubjectInfoDto(
                myRole=subject_info["myRole"],
                situation=subject_info["situation"],
                conversationDate=request.conversationDate,
                messageCount=len(request.messages)
            ),
            scenarios=scenarios
        )

    async def _analyze_conversation_context(self, messages):
        # Call LLM to analyze the conversation
        # Return {"myRole": "...", "situation": "..."}
        pass

    async def _generate_scenario(self, messages, my_role, situation, ai_role, topic_type):
        # Call LLM to generate one scenario
        # Return ScenarioInfoDto
        pass
```

======================================================================
[NEXT STEPS AFTER IMPLEMENTATION]
======================================================================

1. Implement the FastAPI endpoint as specified above
2. Test with sample Slack conversations
3. Integrate with Spring 2:
   - Spring 2 will call your endpoint
   - Your endpoint analyzes and generates scenarios
   - Spring 2 saves the results to MySQL
4. User flow:
   - User selects a date in the UI
   - Spring 1 Gateway → Spring 2 → Your FastAPI endpoint
   - Scenarios are generated and saved
   - User can practice with any of the 6 generated scenarios

======================================================================
End of Slack Scenario Generation Script
======================================================================