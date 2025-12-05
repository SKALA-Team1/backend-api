"""
LLM Scenario Title Generator Service
====================================

시나리오 상황 설명으로부터 완전한 문장 형태의 제목을 생성합니다.

역할:
- 시나리오 상황을 분석하여 설명적인 제목 생성
- 문법적으로 완전한 문장 생성 (중간에 끝나지 않음)
- 최대 200자 제한

예시:
    generator = ScenarioTitleGeneratorImpl()
    title = await generator.generate_title(
        situation="회사의 결제 서비스가 데이터베이스 오류로 중단된 상황"
    )
    # "회사의 결제 서비스가 데이터베이스 오류로 인해 중단되었을 때 대응하는 방법."

의존성:
    - app.roleplaying.services.llm_base (LLM 초기화)
    - app.roleplaying.prompts.constants (프롬프트 관리)
"""

import logging
from app.config import settings
from app.roleplaying.services.llm.llm_base import LLMServiceBase
from app.roleplaying.prompts.constants import SCENARIO_TITLE_GENERATION_PROMPT

logger = logging.getLogger(__name__)


class ScenarioTitleGeneratorImpl(LLMServiceBase):
    """
    시나리오 제목 생성 서비스

    상황 설명으로부터 완전하고 설명적인 제목을 생성합니다.

    책임:
        - 상황 설명을 분석하여 관련 제목 생성
        - 문법적으로 완전한 문장 보장
        - 최대 200자 제한 내에서 설명적인 제목 제공

    의존성:
        - LLMServiceBase (LLM 프로바이더)
        - SCENARIO_TITLE_GENERATION_PROMPT (제목 생성 프롬프트)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """
        시나리오 제목 생성기 초기화

        Args:
            api_key: OpenAI API 키 (기본값: settings.openai_api_key)
            model_name: 모델명 (기본값: settings.OPENAI_MODEL)
            temperature: 창의성 레벨 (기본값: 0.7)
        """
        super().__init__(
            api_key=api_key,
            model_name=model_name or settings.OPENAI_MODEL,
            temperature=temperature
        )

    async def generate_title(self, situation: str) -> str:
        """
        시나리오 상황으로부터 제목 생성

        상황 설명을 받아 LLM이 적절한 제목을 생성합니다.
        생성된 제목은 다음 특징을 가집니다:
        - 완전한 문장 형태 (문법적으로 올바름)
        - 설명적 (상황의 핵심을 반영)
        - 최대 80자 (길이 제한)

        Args:
            situation: 시나리오 상황 설명 (예: "회사의 결제 서비스가 데이터베이스 오류로 중단된 상황")

        Returns:
            생성된 제목 (완전한 문장, 최대 80자)

        예시:
            title = await generator.generate_title(
                situation="회사의 결제 서비스가 데이터베이스 오류로 중단된 상황"
            )
            # "결제 서비스 데이터베이스 오류 대응."
        """
        try:
            # ====================================
            # Step 1: 프롬프트 구성
            # ====================================
            prompt = SCENARIO_TITLE_GENERATION_PROMPT.format(situation=situation)
            logger.info(f"🔹 LLM 호출 전 프롬프트 길이: {len(prompt)}자")

            # ====================================
            # Step 2: LLM 호출
            # ====================================
            logger.info("📝 LLM으로 제목 생성 중...")
            title = await self.llm.invoke(prompt)
            logger.info(f"🔹 LLM 반환값 (처리 전): '{title}'")
            logger.info(f"🔹 LLM 반환 길이: {len(title)}자")

            title = title.strip()
            logger.info(f"🔹 strip() 후: '{title}'")
            logger.info(f"🔹 strip() 후 길이: {len(title)}자")

            # ====================================
            # Step 3: 길이 제한 적용 (80자)
            # ====================================
            if len(title) > 80:
                logger.warning(f"⚠️  제목이 80자 초과 ({len(title)}자) - 자르기 시작")
                # 80자 초과 시 마지막 완전한 문장까지만 추출
                title = title[:80].rstrip()
                logger.info(f"🔹 80자 자른 후: '{title}'")
                logger.info(f"🔹 길이: {len(title)}자")

                # 마지막 문장 부호 찾아서 그 위치까지만 유지
                for punct in ["。", ".", "!", "?"]:
                    last_punct = title.rfind(punct)
                    if last_punct > 0:
                        title = title[:last_punct + 1]
                        logger.info(f"🔹 문장 부호 '{punct}' 찾음 (위치: {last_punct}) → '{title}'")
                        break

            logger.info(f"✅ [최종 제목] '{title}'")
            logger.info(f"✅ [최종 길이] {len(title)}자 (제한: 80자)")
            return title

        except Exception as e:
            logger.error(f"❌ Title generation failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 상황의 첫 문장 반환
            # ====================================
            fallback = self._extract_first_sentence(situation)
            logger.info(f"⚠️  폴백 제목 사용: '{fallback}' ({len(fallback)}자)")
            return fallback

    @staticmethod
    def _extract_first_sentence(text: str) -> str:
        """
        텍스트에서 첫 번째 완전한 문장 추출

        LLM 호출 실패 시 폴백으로 사용.

        Args:
            text: 원본 텍스트

        Returns:
            첫 번째 문장 (없으면 원본 텍스트, 최대 200자)
        """
        if not text:
            return "Roleplay Scenario"

        # 문장 부호 위치 찾기
        for punct in ["。", ".", "!", "?"]:
            pos = text.find(punct)
            if pos > 0:
                sentence = text[:pos + 1]
                if len(sentence) <= 200:
                    return sentence

        # 문장 부호가 없으면 원본 텍스트 반환 (200자 제한)
        if len(text) > 200:
            return text[:200] + "."
        return text + "." if not text.endswith((".", "!", "?")) else text