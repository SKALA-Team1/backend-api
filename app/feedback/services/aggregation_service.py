"""
📄 파일명: aggregation_service.py
📌 역할: 시나리오 종료 후 전체 대화의 피드백 데이터를 집계하고 종합 피드백 생성.
        - 각 발화의 세부 피드백을 수집하여 총점, 평균점수, 종합 피드백을 생성.
🧩 관련 모듈:
  - builder.prompt_builder : 프롬프트 생성
  - builder.response_parser : LLM 응답 파싱
🧠 주요 기능:
  - generate_comprehensive_feedback(): 종합 피드백 생성 (DB 조회 → GPT-4 → 점수 계산)
"""

import json
import logging
from typing import Optional, Dict, List
from sqlalchemy import text
from sqlalchemy.orm import Session
import httpx

from app.config import settings
from app.feedback.builder.prompt_builder import build_comprehensive_feedback_prompt
from app.feedback.builder.response_parser import parse_comprehensive_feedback_response

logger = logging.getLogger(__name__)


async def generate_comprehensive_feedback(
    session_id: str,
    db: Session
) -> Optional[Dict]:
    """
    세션의 종합 피드백 생성

    Args:
        session_id: 롤플레잉 세션 ID
        db: SQLAlchemy 세션

    Returns:
        {
            "feedback_long": "...",
            "feedback_short": "...",
            "total_pronunciation": 85.5,
            "total_grammar": 78.3,
            "total_diversity": 82.0  # relevance_score의 평균
        }
        또는 None (생성 실패)

    Raises:
        Exception: DB 조회 실패, LLM 호출 실패 등
    """
    try:
        logger.info(f"📊 [종합 피드백 생성 시작] session_id={session_id}")

        # ========================================
        # Step 1: DB에서 데이터 조회
        # ========================================
        utterances_data = _fetch_utterances_from_db(session_id, db)

        if not utterances_data:
            logger.warning(f"No utterances found for session: {session_id}")
            return None

        # ========================================
        # Step 2: 발화 목록 포맷팅 (프롬프트용)
        # ========================================
        utterances = []
        pronunciation_scores = []
        grammar_scores = []
        relevance_scores = []

        for utt in utterances_data:
            # feedback_sections JSON 파싱
            feedback_sections = utt.get("feedback_sections")
            if isinstance(feedback_sections, str):
                try:
                    feedback_sections = json.loads(feedback_sections)
                except json.JSONDecodeError:
                    feedback_sections = []

            # 각 섹션에서 한글 피드백 추출
            pronunciation_feedback_ko = ""
            grammar_feedback_ko = ""
            relevance_feedback_ko = ""

            if feedback_sections:
                for section in feedback_sections:
                    section_type = section.get("type")
                    feedback_ko = section.get("feedback_ko", "")

                    if section_type == "pronunciation":
                        pronunciation_feedback_ko = feedback_ko
                    elif section_type == "grammar":
                        grammar_feedback_ko = feedback_ko
                    elif section_type == "relevance":
                        relevance_feedback_ko = feedback_ko

            # 발화 데이터 구성
            utterance = {
                "user_text": utt.get("message_text", ""),
                "pronunciation_score": utt.get("pronunciation_score"),
                "pronunciation_feedback_ko": pronunciation_feedback_ko,
                "grammar_score": utt.get("grammar_score"),
                "grammar_feedback_ko": grammar_feedback_ko,
                "relevance_score": utt.get("relevance_score"),
                "relevance_feedback_ko": relevance_feedback_ko,
            }

            utterances.append(utterance)

            # 점수 수집 (평균 계산용)
            if utt.get("pronunciation_score") is not None:
                pronunciation_scores.append(utt["pronunciation_score"])
            if utt.get("grammar_score") is not None:
                grammar_scores.append(utt["grammar_score"])
            if utt.get("relevance_score") is not None:
                relevance_scores.append(utt["relevance_score"])

        logger.info(f"📝 발화 개수: {len(utterances)}, 점수 수집: pronunciation={len(pronunciation_scores)}, grammar={len(grammar_scores)}, relevance={len(relevance_scores)}")

        # ========================================
        # Step 3: 평균 점수 계산
        # ========================================
        total_pronunciation = round(sum(pronunciation_scores) / len(pronunciation_scores), 1) if pronunciation_scores else None
        total_grammar = round(sum(grammar_scores) / len(grammar_scores), 1) if grammar_scores else None
        total_diversity = round(sum(relevance_scores) / len(relevance_scores), 1) if relevance_scores else None

        logger.info(f"📊 평균 점수: pronunciation={total_pronunciation}, grammar={total_grammar}, diversity={total_diversity}")

        # ========================================
        # Step 4: 프롬프트 생성
        # ========================================
        prompt = build_comprehensive_feedback_prompt(
            utterances=utterances
        )

        logger.debug(f"🔍 Generated prompt length: {len(prompt)} characters")

        # ========================================
        # Step 5: GPT-4 호출
        # ========================================
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL_FEEDBACK,  # gpt-4.1
                messages=[
                    {"role": "system", "content": "You are an IT communication mentor."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            response_text = response.choices[0].message.content
            logger.info(f"✅ GPT-4 응답 받음: {len(response_text)} characters")
            logger.debug(f"🔍 GPT-4 raw response: {response_text[:300]}...")

        except Exception as e:
            logger.error(f"❌ GPT-4 호출 실패: {e}", exc_info=True)
            return None

        # ========================================
        # Step 6: 응답 파싱
        # ========================================
        parsed_feedback = parse_comprehensive_feedback_response(response_text)

        if not parsed_feedback:
            logger.error("❌ 피드백 파싱 실패")
            return None

        # ========================================
        # Step 7: 최종 결과 구성 (점수 → 짧은 피드백 → 긴 피드백 순서)
        # ========================================
        result = {
            "total_pronunciation": total_pronunciation,
            "total_grammar": total_grammar,
            "total_diversity": total_diversity,
            "feedback_short": parsed_feedback["feedback_short"],
            "feedback_long": parsed_feedback["feedback_long"]
        }

        logger.info(f"🎉 [종합 피드백 생성 완료] session_id={session_id}")

        # ========================================
        # Step 8: Spring 2 API를 통해 DB에 저장
        # ========================================
        try:
            await _save_to_spring2(session_id, result)
            logger.info(f"✅ Spring 2 API를 통해 DB 저장 완료: session_id={session_id}")
        except Exception as e:
            logger.error(f"❌ Spring 2 API 저장 실패: {e}", exc_info=True)
            # Spring 2 저장 실패해도 결과는 반환

        return result

    except Exception as e:
        logger.error(f"❌ 종합 피드백 생성 실패: {e}", exc_info=True)
        return None


def _fetch_utterances_from_db(session_id: str, db: Session) -> List[Dict]:
    """
    scenario_message 테이블에서 user 발화 조회

    Args:
        session_id: 세션 ID
        db: SQLAlchemy 세션

    Returns:
        발화 리스트
        [
            {
                "message_text": "...",
                "pronunciation_score": 85,
                "grammar_score": 90,
                "relevance_score": 75,
                "feedback_sections": [...]  # JSON
            },
            ...
        ]
    """
    try:
        query = text("""
            SELECT
                message_text,
                pronunciation_score,
                grammar_score,
                relevance_score,
                feedback_sections
            FROM scenario_message
            WHERE session_id = :session_id
              AND speaker = 'user'
              AND (grammar_score IS NOT NULL OR relevance_score IS NOT NULL OR pronunciation_score IS NOT NULL)
            ORDER BY turn_index ASC
        """)

        result = db.execute(query, {"session_id": session_id})
        rows = result.fetchall()

        utterances = []
        for row in rows:
            utterances.append({
                "message_text": row.message_text,
                "pronunciation_score": row.pronunciation_score,
                "grammar_score": row.grammar_score,
                "relevance_score": row.relevance_score,
                "feedback_sections": row.feedback_sections
            })

        logger.info(f"📥 DB 조회 완료: {len(utterances)}개 발화")
        return utterances

    except Exception as e:
        logger.error(f"❌ DB 조회 실패: {e}", exc_info=True)
        return []


async def _save_to_spring2(session_id: str, feedback_data: Dict) -> None:
    """
    Spring 2에 종합 피드백 저장

    Args:
        session_id: 세션 ID
        feedback_data: 종합 피드백 데이터
            {
                "total_pronunciation": 85.5,
                "total_grammar": 78.3,
                "total_diversity": 82.0,
                "feedback_short": "...",
                "feedback_long": "..."
            }

    Raises:
        Exception: HTTP 요청 실패
    """
    spring2_base_url = getattr(settings, 'SPRING2_BASE_URL', 'http://localhost:8081')
    url = f"{spring2_base_url}/internal/sessions/{session_id}/comprehensive-feedback"

    # Spring 2 DTO 형식으로 변환
    payload = {
        "avgPronunciation": feedback_data.get("total_pronunciation"),
        "avgGrammar": feedback_data.get("total_grammar"),
        "avgRelevance": feedback_data.get("total_diversity"),
        "feedbackShort": feedback_data.get("feedback_short"),
        "feedbackLong": feedback_data.get("feedback_long")
    }

    logger.info(f"📤 Spring 2에 종합 피드백 저장 요청: {url}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)

        if response.status_code == 200:
            logger.info(f"✅ Spring 2에 종합 피드백 저장 성공: session_id={session_id}")
        else:
            logger.error(f"❌ Spring 2 저장 실패: status={response.status_code}, body={response.text}")
            raise Exception(f"Spring 2 returned {response.status_code}: {response.text}")
