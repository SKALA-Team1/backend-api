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

        # 2. LLM 프롬프트 생성
        prompt = self._build_prompt(request, context)

        # 3. LLM 호출
        scenario_data = self._call_llm(prompt)

        # 4. 응답 파싱 및 반환
        return self._parse_response(request, scenario_data, context)

    def _build_prompt(
        self,
        request: ScenarioGenerateRequest,
        context: TextbookContext
    ) -> str:
        """LLM 프롬프트 생성"""
        difficulty_config = DIFFICULTY_CONFIG[request.difficulty]
        scenario_config = SCENARIO_TYPE_CONFIG[request.scenario_type]

        prompt = f"""You are an English conversation scenario generator for Korean learners.

## Task
Generate a realistic English conversation scenario based on the following textbook content and requirements.

## Textbook Reference Content
{context.combined_text}

## Requirements
- **Topic**: {request.topic}
- **Scenario Type**: {request.scenario_type.value} ({scenario_config['context']})
- **Difficulty**: {request.difficulty.value}
- **Number of Turns**: {request.num_turns} (each turn alternates between AI and User)
- **Include Korean Hints**: {request.include_korean_hints}

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
    "title": "Scenario title in English",
    "description": "Brief description of the scenario",
    "situation": "Detailed situation description for the learner",
    "user_role": "Description of user's role",
    "ai_role": "Description of AI's role",
    "dialogues": [
        {{
            "turn_number": 1,
            "speaker": "AI",
            "text": "AI's dialogue",
            "korean_hint": "한국어 힌트 (if include_korean_hints is true)",
            "key_expressions": ["expression 1", "expression 2"]
        }},
        {{
            "turn_number": 2,
            "speaker": "User",
            "text": "Suggested user response",
            "korean_hint": "한국어 힌트",
            "key_expressions": ["expression"]
        }}
    ],
    "key_expressions": ["Overall key expressions from the scenario"],
    "vocabulary": ["Important vocabulary words"],
    "grammar_points": ["Grammar points covered"]
}}

## Important Notes
1. Use expressions and vocabulary from the provided textbook content
2. Make the conversation natural and realistic
3. User turns should be appropriate for the learner's level
4. Include useful business English expressions
5. Korean hints should help understanding, not be direct translations

Generate the scenario now:"""

        return prompt

    def _call_llm(self, prompt: str) -> dict:
        """LLM 호출 및 JSON 파싱"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
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
                max_tokens=2000,
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
