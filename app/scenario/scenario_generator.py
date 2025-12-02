"""
Scenario Generator Service (에이전트2)
======================================
LLM을 활용한 교재 기반 시나리오 생성.

역할:
    - RAG 컨텍스트 기반 시나리오 생성
    - OpenAI GPT를 활용한 대화 시나리오 생성
    - 난이도별 시나리오 조정
"""

import logging
import json
import uuid
from typing import Optional

from openai import OpenAI

from app.config import settings
from app.scenario.schemas import (
    ScenarioGenerateRequest,
    ScenarioResponse,
    ScenarioType,
    DifficultyLevel,
    DialogueTurn
)
from app.scenario.rag_service import get_rag_service, TextbookContext

logger = logging.getLogger(__name__)


# 난이도별 설정
DIFFICULTY_CONFIG = {
    DifficultyLevel.BEGINNER: {
        "vocab_level": "basic vocabulary with common words",
        "sentence_complexity": "short, simple sentences",
        "speed": "slow and clear",
        "hints": "provide detailed Korean translations"
    },
    DifficultyLevel.INTERMEDIATE: {
        "vocab_level": "business vocabulary with some idioms",
        "sentence_complexity": "varied sentence structures",
        "speed": "natural pace",
        "hints": "provide key phrase translations"
    },
    DifficultyLevel.ADVANCED: {
        "vocab_level": "advanced vocabulary with idioms and nuances",
        "sentence_complexity": "complex sentences with subordinate clauses",
        "speed": "fast and natural",
        "hints": "minimal hints, only for difficult expressions"
    }
}

# 시나리오 유형별 설정
SCENARIO_TYPE_CONFIG = {
    ScenarioType.BUSINESS_EMAIL: {
        "context": "writing and responding to business emails",
        "roles": ("Email Writer", "Email Recipient"),
        "sample_situations": ["project update", "meeting request", "feedback response"]
    },
    ScenarioType.PHONE_CALL: {
        "context": "professional phone conversations",
        "roles": ("Caller", "Receiver"),
        "sample_situations": ["scheduling appointment", "customer inquiry", "follow-up call"]
    },
    ScenarioType.MEETING: {
        "context": "business meeting discussions",
        "roles": ("Meeting Participant", "Meeting Host"),
        "sample_situations": ["project planning", "status update", "brainstorming session"]
    },
    ScenarioType.PRESENTATION: {
        "context": "giving and attending presentations",
        "roles": ("Presenter", "Audience Member"),
        "sample_situations": ["quarterly report", "product launch", "training session"]
    },
    ScenarioType.NEGOTIATION: {
        "context": "business negotiations",
        "roles": ("Negotiator", "Counterpart"),
        "sample_situations": ["contract terms", "price negotiation", "partnership discussion"]
    },
    ScenarioType.CUSTOMER_SERVICE: {
        "context": "customer service interactions",
        "roles": ("Customer", "Service Representative"),
        "sample_situations": ["product inquiry", "complaint handling", "refund request"]
    },
    ScenarioType.INTERVIEW: {
        "context": "job interviews",
        "roles": ("Candidate", "Interviewer"),
        "sample_situations": ["self introduction", "experience discussion", "salary negotiation"]
    },
    ScenarioType.GENERAL: {
        "context": "general business conversations",
        "roles": ("Speaker A", "Speaker B"),
        "sample_situations": ["small talk", "networking", "casual discussion"]
    }
}


class ScenarioGenerator:
    """시나리오 생성 서비스"""

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required for scenario generation")

        self.client = OpenAI(api_key=settings.openai_api_key)
        self.rag_service = get_rag_service()
        logger.info("ScenarioGenerator initialized")

    def generate_scenario(self, request: ScenarioGenerateRequest) -> ScenarioResponse:
        """
        시나리오 생성

        Args:
            request: 시나리오 생성 요청

        Returns:
            생성된 시나리오
        """
        # 1. RAG 검색으로 교재 컨텍스트 조회
        context = self.rag_service.get_context_for_scenario(
            topic=request.topic,
            scenario_type=request.scenario_type.value,
            n_results=5,
            chapter_filter=request.chapter_filter
        )

        logger.info(f"Retrieved context from chapters: {context.chapters}")

        # 2. 2단계 생성 방식 (10턴씩)
        if request.num_turns > 10:
            return self._generate_long_scenario(request, context)
        else:
            # 10턴 이하는 한 번에 생성
            prompt = self._build_prompt(request, context)
            scenario_data = self._call_llm(prompt)
            return self._parse_response(request, scenario_data, context)

    def _generate_long_scenario(
        self,
        request: ScenarioGenerateRequest,
        context: TextbookContext
    ) -> ScenarioResponse:
        """
        긴 시나리오를 2단계로 생성 (10턴씩)

        Args:
            request: 시나리오 생성 요청
            context: RAG 컨텍스트

        Returns:
            생성된 시나리오
        """
        # Phase 1: 첫 10턴 생성
        logger.info(f"Generating first 10 turns...")
        first_request = ScenarioGenerateRequest(
            user_id=request.user_id,
            topic=request.topic,
            scenario_type=request.scenario_type,
            difficulty=request.difficulty,
            num_turns=10,
            chapter_filter=request.chapter_filter,
            include_korean_hints=request.include_korean_hints,
            save_to_db=False
        )

        first_prompt = self._build_prompt(first_request, context)
        first_data = self._call_llm(first_prompt)

        # Phase 2: 나머지 턴 생성
        remaining_turns = request.num_turns - 10
        logger.info(f"Generating remaining {remaining_turns} turns...")

        # 첫 10턴의 대화 내용을 컨텍스트로 전달
        second_prompt = self._build_continuation_prompt(
            request=request,
            context=context,
            previous_dialogues=first_data.get("dialogues", []),
            start_turn=11,
            num_turns=remaining_turns
        )

        second_data = self._call_llm(second_prompt)

        # 두 결과 병합
        merged_data = {
            "title": first_data.get("title", f"{request.topic} Scenario"),
            "description": first_data.get("description", ""),
            "situation": first_data.get("situation", ""),
            "user_role": first_data.get("user_role", ""),
            "ai_role": first_data.get("ai_role", ""),
            "dialogues": first_data.get("dialogues", []) + second_data.get("dialogues", []),
            "key_expressions": list(set(
                first_data.get("key_expressions", []) +
                second_data.get("key_expressions", [])
            )),
            "vocabulary": list(set(
                first_data.get("vocabulary", []) +
                second_data.get("vocabulary", [])
            )),
            "grammar_points": list(set(
                first_data.get("grammar_points", []) +
                second_data.get("grammar_points", [])
            ))
        }

        logger.info(f"Merged scenario: {len(merged_data['dialogues'])} total turns")

        return self._parse_response(request, merged_data, context)

    def _build_continuation_prompt(
        self,
        request: ScenarioGenerateRequest,
        context: TextbookContext,
        previous_dialogues: list[dict],
        start_turn: int,
        num_turns: int
    ) -> str:
        """후속 턴 생성용 프롬프트"""
        difficulty_config = DIFFICULTY_CONFIG[request.difficulty]
        scenario_config = SCENARIO_TYPE_CONFIG[request.scenario_type]

        # 이전 대화 요약
        prev_summary = "\n".join([
            f"Turn {d.get('turn_number')}: {d.get('speaker')} - {d.get('text')[:50]}..."
            for d in previous_dialogues[-4:]  # 마지막 4턴만
        ])

        prompt = f"""You are an expert English conversation scenario generator for Korean learners.

## Task
Continue the existing conversation scenario with {num_turns} more turns, starting from turn {start_turn}.

## Previous Conversation Context
{prev_summary}

## Textbook Reference Content
{context.combined_text}

## Requirements
- **Topic**: {request.topic}
- **Scenario Type**: {request.scenario_type.value}
- **Difficulty**: {request.difficulty.value}
- **Continue from Turn**: {start_turn}
- **Additional Turns**: {num_turns}

  ⚠️ CRITICAL REQUIREMENT:
  - Generate EXACTLY {num_turns} more turns
  - Start turn_number from {start_turn}
  - Continue alternating: {'AI' if start_turn % 2 == 1 else 'User'} speaks on turn {start_turn}, then alternate
  - End at turn {start_turn + num_turns - 1}

## Output Format (JSON)
{{
    "dialogues": [
        {{"turn_number": {start_turn}, "speaker": "{'AI' if start_turn % 2 == 1 else 'User'}", "text": "continuation...", "korean_hint": "한국어 힌트", "key_expressions": ["expression"]}},
        ... continue for {num_turns} turns ...
    ],
    "key_expressions": ["Additional key expressions"],
    "vocabulary": ["Additional vocabulary"],
    "grammar_points": ["Additional grammar points"]
}}

Generate the continuation now:"""

        return prompt

    def _build_prompt(
        self,
        request: ScenarioGenerateRequest,
        context: TextbookContext
    ) -> str:
        """LLM 프롬프트 생성"""
        difficulty_config = DIFFICULTY_CONFIG[request.difficulty]
        scenario_config = SCENARIO_TYPE_CONFIG[request.scenario_type]

        # 챕터 제목에서 영어 제목 추출 (예: "Chapter 01: Starting a Meeting (미팅에서의 기본 태도)" -> "Starting a Meeting")
        chapter_title = request.chapter_filter
        if ": " in chapter_title:
            english_title = chapter_title.split(": ")[1].split(" (")[0]
        else:
            english_title = chapter_title

        prompt = f"""You are an English conversation scenario generator for Korean learners.

## Task
Generate a realistic English conversation scenario based on the following textbook content.
⚠️ **IMPORTANT**: You MUST closely follow the dialogues, expressions, and vocabulary from the textbook content below.

## Textbook Reference Content (교재 원본 내용)
{context.combined_text}

## Scenario Title (FIXED - DO NOT CHANGE)
**Title**: "{english_title}"

## Requirements
- **Chapter**: {request.chapter_filter}
- **Scenario Type**: {request.scenario_type.value} ({scenario_config['context']})
- **Difficulty**: {request.difficulty.value}
- **Number of Turns**: {request.num_turns} turns total

  ⚠️ CRITICAL REQUIREMENT - MUST FOLLOW EXACTLY:
  - Total turns MUST be exactly {request.num_turns}
  - AI speaks: {request.num_turns // 2} times (turns 1, 3, 5, 7, 9, 11, 13, 15, 17, 19...)
  - User responds: {request.num_turns // 2} times (turns 2, 4, 6, 8, 10, 12, 14, 16, 18, 20...)
  - Alternating pattern: AI → User → AI → User → ... until turn {request.num_turns}
  - DO NOT STOP until you have generated ALL {request.num_turns} turns!

- **Include Korean Hints**: {request.include_korean_hints}

## ⚠️ CRITICAL: Use Textbook Content
1. **MUST use the exact expressions and sentences from the textbook** when possible
2. **MUST include the key vocabulary** mentioned in the textbook
3. **MUST follow the situation/scenario** described in the textbook
4. The dialogues should feel like they came directly from the textbook examples

## Difficulty Guidelines
- Vocabulary Level: {difficulty_config['vocab_level']}
- Sentence Complexity: {difficulty_config['sentence_complexity']}
- Speaking Speed: {difficulty_config['speed']}
- Hints: {difficulty_config['hints']}

## Role Assignment
- AI Role: {scenario_config['roles'][0]}
- User Role: {scenario_config['roles'][1]}

## Output Format (JSON)
{{
    "title": "{english_title}",
    "description": "Brief description based on textbook learning objectives",
    "situation": "Detailed situation description for the learner",
    "user_role": "Description of user's role",
    "ai_role": "Description of AI's role",
    "dialogues": [
        {{"turn_number": 1, "speaker": "AI", "text": "AI's dialogue in English", "korean_hint": "AI 영어 문장의 정확한 한국어 번역", "key_expressions": ["expression"]}},
        {{"turn_number": 2, "speaker": "User", "text": "User's response in English", "korean_hint": "User가 말해야 할 영어 문장의 정확한 한국어 번역", "key_expressions": ["expression"]}},
        {{"turn_number": 3, "speaker": "AI", "text": "AI's dialogue in English", "korean_hint": "AI 영어 문장의 정확한 한국어 번역", "key_expressions": ["expression"]}},
        {{"turn_number": 4, "speaker": "User", "text": "User's response in English", "korean_hint": "User가 말해야 할 영어 문장의 정확한 한국어 번역", "key_expressions": ["expression"]}},
        ... continue alternating AI/User until turn {request.num_turns} ...
    ],
    "key_expressions": ["Overall key expressions from the scenario"],
    "vocabulary": ["Important vocabulary words"],
    "grammar_points": ["Grammar points covered"]
}}

## Important Notes - Korean Hints
**CRITICAL**: The korean_hint field MUST be a DIRECT KOREAN TRANSLATION of the English text, NOT an explanation.

✅ CORRECT korean_hint example:
- English: "I am writing to request an extension on the monthly report deadline."
- korean_hint: "저는 월간 보고서 마감일 연장을 요청드립니다."

❌ WRONG korean_hint example (DO NOT DO THIS):
- English: "I am writing to request an extension on the monthly report deadline."
- korean_hint: "상대방에게 마감일 연장을 요청하는 내용입니다." (This is an explanation, NOT a translation)

The learner will READ the Korean sentence and SPEAK it in English. So korean_hint must be a sentence they can directly translate.

## Other Important Notes
1. **PRIORITY**: Use the EXACT expressions, sentences, and dialogues from the textbook content above
2. Include the key vocabulary and business idioms from the textbook
3. Follow the situation examples (Situation 01, Situation 02) from the textbook
4. User turns should match the textbook's learning objectives
5. **CRITICAL**: The dialogues array MUST contain exactly {request.num_turns} turns, with AI and User alternating.
6. The scenario title MUST be exactly: "{english_title}"

Generate the scenario based on the textbook content now:"""

        return prompt

    def _call_llm(self, prompt: str) -> dict:
        """LLM 호출 및 JSON 파싱"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert English education content creator. Always respond with valid JSON only, no additional text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=3500,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError("Failed to generate valid scenario")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_response(
        self,
        request: ScenarioGenerateRequest,
        data: dict,
        context: TextbookContext
    ) -> ScenarioResponse:
        """LLM 응답을 ScenarioResponse로 변환"""
        # 대화 턴 파싱
        dialogues = []
        for turn_data in data.get("dialogues", []):
            dialogue = DialogueTurn(
                turn_number=turn_data.get("turn_number", len(dialogues) + 1),
                speaker=turn_data.get("speaker", "AI"),
                text=turn_data.get("text", ""),
                korean_hint=turn_data.get("korean_hint") if request.include_korean_hints else None,
                key_expressions=turn_data.get("key_expressions", [])
            )
            dialogues.append(dialogue)

        # 검증: AI와 User 발화 횟수 체크
        ai_count = sum(1 for d in dialogues if d.speaker == "AI")
        user_count = sum(1 for d in dialogues if d.speaker == "User")
        expected_each = request.num_turns // 2

        if ai_count != expected_each or user_count != expected_each:
            logger.warning(
                f"Turn count mismatch: AI={ai_count} (expected {expected_each}), "
                f"User={user_count} (expected {expected_each}). Total turns: {len(dialogues)}"
            )

        return ScenarioResponse(
            scenario_id=str(uuid.uuid4()),
            title=data.get("title", f"{request.topic} Scenario"),
            description=data.get("description", ""),
            scenario_type=request.scenario_type,
            difficulty=request.difficulty,
            situation=data.get("situation", ""),
            user_role=data.get("user_role", ""),
            ai_role=data.get("ai_role", ""),
            dialogues=dialogues,
            key_expressions=data.get("key_expressions", []),
            vocabulary=data.get("vocabulary", []),
            grammar_points=data.get("grammar_points", []),
            source_chapters=context.chapters
        )


# 싱글톤 인스턴스
_generator: Optional[ScenarioGenerator] = None


def get_scenario_generator() -> ScenarioGenerator:
    """ScenarioGenerator 싱글톤 반환"""
    global _generator
    if _generator is None:
        _generator = ScenarioGenerator()
    return _generator
