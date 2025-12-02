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
사용자 요약: {user_summary}

상대방 요약: {counterpart_summary}

위 대화를 기반으로 영어 연습을 위한 정확히 3개의 follow-up 질문을 생성해주세요.
각 질문은 자연스럽고 실용적이어야 합니다.

JSON 형식으로 다음과 같이 응답하세요:
{{"questions": ["질문1", "질문2", "질문3"]}}

응답은 유효한 JSON만 포함하세요.
"""

PROMPT_QUESTIONS_PROMPT = """
상황: {situation}
사용자 역할: {my_role}
AI 역할: {ai_role}

위 상황에서 영어 연습을 위한 정확히 3개의 질문을 생성해주세요.
1. 대화 시작 질문
2. 중간 심화 질문
3. 마무리 질문

JSON 형식으로 다음과 같이 응답하세요:
{{"questions": ["질문1", "질문2", "질문3"]}}

응답은 유효한 JSON만 포함하세요.
"""

# ============================================
# 평가/피드백 프롬프트
# ============================================

GRAMMAR_EVALUATION_PROMPT = """문법 평가: "{user_text}"
점수(0-100)와 간단한 피드백만 JSON으로 응답:
{{"score": int, "feedback": str}}"""

RELEVANCE_EVALUATION_PROMPT = """맥락 평가: "{context}"
응답: "{user_text}"
점수(0-100)와 간단한 피드백만 JSON:
{{"score": int, "feedback": str}}"""

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
상황: {situation}
사용자 역할: {my_role}
AI 역할: {ai_role}

위 상황의 핵심을 담은 짧은 제목(5-10단어)을 만들어주세요.
제목만 출력하고 다른 설명은 포함하지 마세요.
"""