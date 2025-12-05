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
{{"questions": ["question1", "question2", "question3"]}}

Return valid JSON only.
"""


# ============================================
# 평가/피드백 프롬프트
# ============================================

GRAMMAR_EVALUATION_PROMPT = """
Grammar Evaluation Target: "{user_text}"

Evaluation Principles (only mention issues actually present):
- Verb tense consistency in technical explanations or process descriptions
- Subject-verb agreement
- Article usage (especially in technical nouns like "API", "server", "deployment")
- Preposition accuracy in common IT expressions ("on the server", "in production", "for testing")
- Sentence clarity and structure (avoid ambiguity in requirements, tasks, or steps)

For each issue found:
- Briefly explain why it is an issue (1 sentence)
- Do NOT provide improved versions or examples (they will be provided separately)

Include positive reinforcement:
- If the sentence has strengths (clarity, vocabulary, structure), mention them briefly.

If no grammatical or clarity issues exist, explicitly return:
"No grammatical issues detected. Clear and effective communication."

Strict JSON format:
{{"score": int (0-100), "feedback": "specific issues only OR 'No grammatical issues detected. Clear and effective communication.'"}}
"""

RELEVANCE_EVALUATION_PROMPT = """
Context Relevance Evaluation for IT English Training

Question: "{context}"
User Response: "{user_text}"

Evaluation Criteria (mention only actual issues found):
- Understanding: Did the user clearly understand the technical intention of the question?
- Directness: Did the response stay on-topic and avoid unrelated details?
- Specificity: Did the response include concrete examples (systems, tasks, tools, processes)?
- Completeness: Did the response cover all components of the question (e.g., cause, action, result)?
- Communication Quality: Would this response be effective in an actual workplace discussion?

For each shortcoming:
- Explain why it matters in real developer communication
- Do NOT provide examples of improvements (they will be provided separately)

If the response is strong and workplace-ready, return:
"Response adequately, specifically, and professionally addresses the question."

Strict JSON format:
{{"score": int (0-100), "feedback": "specific shortcomings only OR 'Response adequately, specifically, and professionally addresses the question.'"}}
"""

PRONUNCIATION_FEEDBACK_PROMPT = """
Pronunciation Evaluation for IT English Training

User Text: "{user_text}"

Pronunciation Scores (from Azure Speech Service):
- Pronunciation Score: {pronunciation_score}/100 (overall quality)
- Accuracy Score: {accuracy_score}/100 (correct phonemes)
- Fluency Score: {fluency_score}/100 (smoothness and rhythm)
- Completeness Score: {completeness_score}/100 (all phonemes present)
- Words with Errors: {error_words}

Evaluation Task:
Based on the pronunciation scores above, provide constructive feedback that:
1. Identifies the main pronunciation issues (if any)
2. Explains why clear pronunciation matters in professional IT communication
3. Provides specific, actionable guidance for improvement
4. Does NOT include corrected examples (they will be provided separately)

Guidelines:
- If pronunciation_score >= 80: Acknowledge good performance
- If pronunciation_score < 80: Identify areas for improvement (accuracy, fluency, completeness)
- Focus on clarity and professionalism for IT domain communication
- Keep feedback concise and encouraging

If pronunciation is strong and professional, return:
"Pronunciation is clear and professional. Well done!"

Strict JSON format:
{{"score": int (0-100), "feedback": "specific issues only OR 'Pronunciation is clear and professional. Well done!'"}}
"""

# ============================================
# 시나리오/상황 생성 프롬프트
# ============================================

CONVERSATION_ANALYSIS_PROMPT = """
Conversation to Analyze:
{conversation_text}

Role: {my_role}
Date: {conversation_date}

Please provide a brief analysis of the core situation in 2–3 sentences.
The goal is to identify the main topics and the context.
"""

SCENARIO_GENERATION_PROMPT = """
Situation: {situation}
User Role: {my_role}
AI Role: {ai_role}

Please generate an English-practice scenario based on the situation above.

Provide the response in valid JSON containing:
1. opening_question: a question to start the conversation
2. questions: exactly 3 follow-up questions (array)
3. context: background description of the scenario

Return only the JSON output.
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
Role Settings:
- You are {ai_role}.
- The other person is {my_role}.

Situation: {situation}

Conversation:
{history_text}

Respond naturally to the latest message from {my_role}.
Provide a professional and helpful response.
"""

MESSAGE_SUMMARY_PROMPT = """
Below are messages from the perspective of {perspective}:

{messages_text}

Please provide a brief summary of these messages.
Summarize the core content in 2–3 sentences.
"""

TITLE_GENERATION_PROMPT = """
Situation: {situation}
User Role: {my_role}
AI Role: {ai_role}

Create a short title (5–10 words) that captures the core of the situation.
Output only the title and include no additional explanation.
"""

# ============================================
# ReAct Agent Prompts (Feedback Decision)
# ============================================

FEEDBACK_DECISION_AGENT_SYSTEM_PROMPT = """You are a ReAct agent responsible for evaluating English learners' responses and deciding whether to provide corrective feedback or proceed to the next question.

Your role:
You analyze evaluation scores and conversation context to make intelligent decisions that balance learning effectiveness with user motivation.

Decision Criteria (in priority order):

1. **All evaluations failed?**
   - If pronunciation_score, grammar_score, and relevance_score are all None → NEXT_QUESTION (no feedback data available)

2. **Max retries exceeded?**
   - If retry_count >= 3 → NEXT_QUESTION (force pass after 3 attempts)

3. **Critical pronunciation issues?**
   - If pronunciation_score < 65 AND pronunciation_score is not None → FEEDBACK (pronunciation priority)

4. **Significant grammar errors?**
   - If grammar_score < 70 AND pronunciation issues not found → FEEDBACK (grammar priority)

5. **Response doesn't address the question?**
   - If relevance_score < 75 AND no grammar/pronunciation issues → FEEDBACK (relevance priority)

6. **Learner has done well enough?**
   - If all scores >= 70 OR no major issues detected → NEXT_QUESTION (encourage progress)

Context:
- User Role: {my_role}
- AI Role: {ai_role}
- Current Question: {current_question}
- Retry Count: {retry_count}/3
- Evaluation Scores:
  * Pronunciation: {pronunciation_score}
  * Grammar: {grammar_score}
  * Relevance: {relevance_score}
  * Overall: {overall_score}

Important Principles:
- Be encouraging but honest about areas for improvement
- Remember that over-correcting discourages learners
- Balance learning rigor with learner motivation
- Consider the learner's effort and progress

Your task:
Based on the evaluation scores and context above, decide whether to provide FEEDBACK or proceed to the NEXT_QUESTION.

Respond in valid JSON format ONLY:
{{
    "action": "FEEDBACK" or "NEXT_QUESTION",
    "reasoning": "Brief explanation (1-2 sentences) of why you chose this action",
    "confidence": <float between 0.0 and 1.0>
}}

Do not include any other text, explanations, or commentary.
"""

# ============================================
# Translation Prompts (Bilingual Support)
# ============================================

KOREAN_TRANSLATION_PROMPT = """
Translate the following English text to Korean.

Rules:
1. Maintain technical accuracy and professional tone
2. Use appropriate IT/business Korean terminology
3. Preserve the original meaning and intent
4. Keep formatting and structure intact
5. Translate field names/labels as-is (no translation needed)

English Text to Translate:
"{english_text}"

Provide ONLY the Korean translation, no other text.
"""

FEEDBACK_BILINGUAL_PROMPT = """
You are a translator specializing in IT English learning materials.

Translate the provided English feedback to Korean while maintaining:
1. Professional tone appropriate for IT professionals
2. Technical accuracy
3. Learning guidance clarity

English Feedback:
"{english_feedback}"

Provide the response in JSON format ONLY:
{{
    "korean_feedback": "Korean translation of the feedback"
}}

Do not include explanations or other text.
"""

QUESTION_BILINGUAL_PROMPT = """
You are a translator specializing in IT English learning materials.

Translate the provided English question to Korean while maintaining:
1. The original conversational context
2. Professional tone appropriate for IT role-play
3. Clear, natural Korean that encourages detailed response

English Question:
"{english_question}"

Provide the response in JSON format ONLY:
{{
    "korean_question": "Korean translation of the question"
}}

Do not include explanations or other text.
"""

# ============================================
# Recommendation Prompts (Learning Guidance)
# ============================================

RECOMMENDED_KEYWORDS_PROMPT = """
Analyze the Slack message context and AI question to generate highly specific, actionable keywords for the user's response.

Original Slack Message (Scenario Source):
{slack_message}

Current Role Play Context:
Question: "{question}"
User Role: {user_role}
AI Role: {ai_role}
Scenario Background: {scenario_context}

Recent Conversation (Last 2 exchanges):
{conversation_summary}

Task:
Generate 3 specific, domain-focused keywords that:
1. Directly extracted from or closely related to the Slack message content
2. Represent actual technical issues, tools, or processes mentioned in Slack
3. Are appropriate for the user's role in this scenario
4. Guide the user toward a professional, context-aware response
5. Include technical terms, processes, and best practices relevant to the real situation

Priority Guidelines:
- Extract specific keywords FROM the Slack message (highest priority)
- Add related technical terms based on the Slack context
- Consider the actual IT domain (debugging, architecture, deployment, etc.)
- Include tools/technologies mentioned or implied
- Suggest best practices relevant to the specific problem

Examples:
Slack: "DB migration causing latency in production"
Keywords: "database migration", "latency optimization", "connection pooling", "query profiling", "rollback strategy"

Slack: "CI/CD pipeline failing on staging environment"
Keywords: "environment-specific configuration", "pipeline debugging", "staging deployment", "log analysis", "failure recovery"

DO NOT include:
- Generic words (very, important, good, bad)
- Words already in the question
- Instructions or meta-commentary
- Spelling variations of the same concept

Provide the response in JSON format ONLY:
{{
    "keywords": ["keyword1", "keyword2", "keyword3"]
}}

Return valid JSON only.
"""

# ============================================
# 시나리오 제목 생성 프롬프트
# ============================================

SCENARIO_TITLE_GENERATION_PROMPT = """
당신은 IT 영어 대화 연습 시나리오의 제목을 생성하는 어시스턴트입니다.

주어진 상황 설명으로부터 완전하고 설명적인 제목을 생성해야 합니다.

[상황 설명]
{situation}

[작업 요구사항]
다음 조건을 모두 만족하는 제목을 생성하세요:

1. **완전한 문장**: 문법적으로 완벽하고 중간에 끝나지 않아야 합니다.
   - "회사의 결제 서비스가 데이터베이스 오류로 인해 중단된 상황" → "회사의 결제 서비스가 데이터베이스 오류로 인해 중단되었을 때 대응하는 방법."
   - 절대 "회사의 결제 서비스가" 처럼 끝나면 안 됩니다.

2. **설명적**: 상황의 핵심을 명확하게 드러냅니다.
   - 일반적인 제목은 피하세요 (예: "Focused Detail", "Discussion Scenario")
   - 상황의 구체적인 내용을 반영해야 합니다.

3. **길이**: 최대 80자 이내입니다.
   - 너무 짧거나 길지 않으면서도 간결해야 합니다.

4. **언어**: 한국어로 작성합니다.

[출력 형식]
제목 텍스트만 출력하세요. 설명이나 추가 내용은 없어야 합니다.
"""