"""
LLM Service (SOLID 준수)
=======================
분리된 LLM 서비스들의 Facade

구조 (분리됨):
    llm_conversation_analyzer.py    → ConversationAnalyzerImpl
    llm_scenario_generator.py       → ScenarioGeneratorImpl
    llm_question_generator.py       → QuestionGeneratorImpl
    llm_ai_response_generator.py    → AIResponseGeneratorImpl
    llm_message_summarizer.py       → MessageSummarizerImpl
    llm_fixed_question_builder.py   → FixedQuestionBuilderImpl
    llm_scenario_enhancer.py        → ScenarioEnhancerImpl

이 파일:
    - 각 서비스를 import하여 재 export
    - 하위 호환성 제공
    - 필요시 Facade 패턴으로 확장 가능

사용 예시 (기존과 동일):
    from app.roleplaying.services.llm.llm_service import (
        ConversationAnalyzerImpl,
        ScenarioGeneratorImpl,
        QuestionGeneratorImpl,
    )

    analyzer = ConversationAnalyzerImpl()
    scenario = ScenarioGeneratorImpl()
"""

# ============================================
# Facade Imports
# 하위 호환성을 위해 모든 서비스를 import하여 재 export
# ============================================

from app.roleplaying.services.llm.llm_conversation_analyzer import (
    ConversationAnalyzerImpl,
)
from app.roleplaying.services.llm.llm_scenario_generator import (
    ScenarioGeneratorImpl,
)
from app.roleplaying.services.llm.llm_question_generator import (
    QuestionGeneratorImpl,
)
from app.roleplaying.services.llm.llm_ai_response_generator import (
    AIResponseGeneratorImpl,
)
from app.roleplaying.services.llm.llm_message_summarizer import (
    MessageSummarizerImpl,
)
from app.roleplaying.services.llm.llm_fixed_question_builder import (
    FixedQuestionBuilderImpl,
)
from app.roleplaying.services.llm.llm_scenario_enhancer import (
    ScenarioEnhancerImpl,
)

__all__ = [
    "ConversationAnalyzerImpl",
    "ScenarioGeneratorImpl",
    "QuestionGeneratorImpl",
    "AIResponseGeneratorImpl",
    "MessageSummarizerImpl",
    "FixedQuestionBuilderImpl",
    "ScenarioEnhancerImpl",
]
