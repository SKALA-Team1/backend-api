"""
LLM Prompt Constants
===================
모든 LLM 프롬프트 상수를 중앙에서 관리합니다.

분류:
- 질문 생성 프롬프트
- 평가/피드백 프롬프트
- 시나리오 생성 프롬프트
- 기타 생성 프롬프트
"""

# ============================================
# 질문 생성 프롬프트
# ============================================

FOLLOWUP_QUESTION_PROMPT = """You are an AI roleplaying partner acting as a {role} in a professional, IT-focused English conversation training session. 
Your job is to ask the user a contextually appropriate follow-up question based on the scenario and the conversation so far.

----------------------------------------
SCENARIO CONTEXT
----------------------------------------
{scenario_context}

----------------------------------------
CONVERSATION HISTORY
----------------------------------------
{conversation_history}

----------------------------------------
USER'S LATEST MESSAGE
----------------------------------------
"{user_text}"

----------------------------------------
YOUR TASK
----------------------------------------
Generate ONE follow-up question that meets ALL of the following requirements:

1. **Context relevance**  
   - The question must directly relate to what the user just said.  
   - It must reflect understanding of the user’s previous statements, concerns, or updates.

2. **Professional IT domain alignment**  
   The question should be framed as if you are participating in a real IT collaboration scenario, such as:
   - software development planning  
   - debugging or incident handling  
   - project management / sprint updates  
   - system architecture discussions  
   - code reviews  
   - cross-team collaboration  
   - requirement clarification  
   - deployment, CI/CD, or DevOps workflows  
   - communication with stakeholders  

3. **Role consistency**  
   - Stay fully in character as a {role}.  
   - Your tone, vocabulary, and question style should match the responsibilities and communication style of that role  
     (e.g., engineer, PM, QA, tech lead, client stakeholder).

4. **Language learning value**  
   - Encourage the user to speak in detailed, full-sentence, professional English.  
   - Avoid yes/no questions.  
   - Encourage elaboration, clarification, or explanation.

5. **Natural and conversational tone**  
   - Sound like a real professional at work.  
   - Ask only **one** question.  
   - Do NOT add disclaimers, notes, or extra commentary.

----------------------------------------
OUTPUT FORMAT
----------------------------------------
Return ONLY the question text in English.
Do NOT include greetings, explanations, or any additional output.
"""

FIXED_QUESTIONS_PROMPT = """
You are an assistant refining follow-up questions for English conversation practice in an IT collaboration environment.

[Context]
This prompt is used *after analyzing real Slack messages*.  
You will receive two summaries:
- The user's message history
- The counterpart's message history

These summaries represent actual discussions about real IT work, such as debugging, feature work, deployments, planning, code review, team coordination, or decision-making.

Based on these summaries, your job is to generate three highly specific follow-up questions that reflect the real content, motivations, concerns, or actions described in the conversation.

[User Summary]
{user_summary}

[Counterpart Summary]
{counterpart_summary}

Task:
Generate exactly three follow-up questions in English that:

1. Clearly connect to the issues, decisions, blockers, or goals shown in the summaries.  
2. Encourage detailed, professional IT explanations (never yes/no).  
3. Reflect realistic IT communication patterns (engineering, PM, QA, DevOps, cross-team alignment, etc.).  
4. Each question should address a different angle of the conversation, such as:  
   - Root cause or background  
   - Decision rationale  
   - Risks and concerns  
   - Collaboration or coordination  
   - Next steps or actions  

Additional Requirements:
- Questions must be grounded in the Slack summary content (NOT generic).  
- Avoid assumptions not supported by the summaries.  
- Produce only the JSON output below.

Output Format (strict):
{"questions": ["question1", "question2", "question3"]}

Return valid JSON only.
"""


# ============================================
# 평가/피드백 프롬프트
# ============================================

GRAMMAR_EVALUATION_PROMPT = """
Grammar Evaluation Target: "{user_text}"

Evaluation Guidelines (mention only actual issues found):
- Verb tense consistency
- Subject-verb agreement
- Article usage
- Preposition accuracy
- Sentence structure or phrasing
- Mention only real errors, with short concrete examples

If no grammatical errors exist, explicitly return:
"No grammatical errors detected"

JSON response format (strict):
{"score": int (0-100), "feedback": "specific issues OR 'No grammatical errors detected'"}
"""

RELEVANCE_EVALUATION_PROMPT = """
Context Relevance Evaluation

Question: "{context}"
User Response: "{user_text}"

Evaluation Criteria (mention only actual issues):
- Understanding: Did the user grasp the intent of the question?
- Directness: Did the response directly address the question? (no topic drift)
- Specificity: Did the response include details or examples?
- Completeness: Did the response cover all parts of the question without omission?
- Mention only real shortcomings, with concrete justification

If the response sufficiently and specifically answers the question, use:
"Response adequately and specifically addresses the question"

JSON response format (strict):
{"score": int (0-100), "feedback": "specific shortcomings OR 'Response adequately and specifically addresses the question'"}
"""

# ============================================
# 시나리오/상황 생성 프롬프트
# ============================================

CONVERSATION_ANALYSIS_PROMPT = """
분석할 대화:
{conversation_text}

역할: {my_role}
날짜: {conversation_date}

위 대화의 핵심 상황을 2-3문장으로 간단히 분석해주세요.
주요 주제와 상황을 파악하는 것이 목적입니다.
"""

SCENARIO_GENERATION_PROMPT = """
상황: {situation}
사용자 역할: {my_role}
AI 역할: {ai_role}

위 상황에서 영어 연습을 위한 시나리오를 생성해주세요.

JSON 형식으로 다음을 포함해주세요:
1. opening_question: 대화 시작 질문
2. questions: 정확히 3개의 follow-up 질문 (배열)
3. context: 시나리오 배경 설명

응답은 유효한 JSON만 포함하세요.
"""

SITUATION_ENHANCEMENT_PROMPT = """
사용자 역할: {my_role}
AI 역할: {ai_role}

사용자 입력: {situation}

{context_text}

위 정보를 바탕으로 더 구체적인 롤플레이 상황을 만들어주세요.
2-3문장으로 자연스럽고 실무적인 상황을 작성해주세요.
"""

# ============================================
# 기타 생성 프롬프트
# ============================================

AI_RESPONSE_PROMPT = """
역할 설정:
- 당신은 {ai_role}입니다.
- 상대방은 {my_role}입니다.

상황: {situation}

대화:
{history_text}

{my_role}의 발언에 자연스럽게 응답하세요.
전문적이고 도움이 되는 응답을 작성해주세요.
"""

MESSAGE_SUMMARY_PROMPT = """
다음은 {perspective} 관점의 메시지들입니다:

{messages_text}

위 메시지들을 간단히 요약해주세요. 핵심 내용만 2-3문장으로 정리하세요.
"""

TITLE_GENERATION_PROMPT = """
Situation: {situation}
User Role: {my_role}
AI Role: {ai_role}

Create a short title (5–10 words) that captures the core of the situation.
Output only the title and include no additional explanation.
"""