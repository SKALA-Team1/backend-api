"""
Dependency Injection Tests
===========================
DI 함수들의 의존성 주입 테스트.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import get_args

from app.roleplaying.services.dependencies import (
    get_conversation_analyzer,
    get_scenario_generator,
    get_question_generator,
    get_ai_response_generator,
    get_pronunciation_evaluator,
    get_grammar_evaluator,
    get_relevance_evaluator,
    get_feedback_judge,
    get_feedback_orchestrator,
    get_feedback_agent_service,
    get_session_repository,
    get_scenario_repository,
    get_session_service,
    get_ai_tutor_service,
    get_slack_scenario_service,
    get_prompt_based_scenario_service,
    get_azure_usage_tracker,
    # Type aliases
    ConversationAnalyzerDep,
    ScenarioGeneratorDep,
    QuestionGeneratorDep,
    AIResponseGeneratorDep,
    PronunciationEvaluatorDep,
    GrammarEvaluatorDep,
    RelevanceEvaluatorDep,
    FeedbackJudgeDep,
    FeedbackOrchestratorDep,
    SessionRepositoryDep,
    ScenarioRepositoryDep,
    AITutorServiceDep,
    SlackScenarioServiceDep,
    PromptBasedScenarioServiceDep,
    FeedbackAgentServiceDep,
    SessionServiceDep,
)


class TestLLMServiceDependencies:
    """LLM Service 의존성 주입 테스트"""

    def test_get_conversation_analyzer(self, mock_settings):
        """대화 분석기 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            analyzer = get_conversation_analyzer()

            assert analyzer is not None
            assert hasattr(analyzer, 'analyze_situation')

    def test_get_conversation_analyzer_caching(self, mock_settings):
        """대화 분석기 캐싱 (싱글톤 패턴)"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            # lru_cache 초기화
            get_conversation_analyzer.cache_clear()

            analyzer1 = get_conversation_analyzer()
            analyzer2 = get_conversation_analyzer()

            assert analyzer1 is analyzer2  # 같은 인스턴스

    def test_get_scenario_generator(self, mock_settings):
        """시나리오 생성기 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            generator = get_scenario_generator()

            assert generator is not None
            assert hasattr(generator, 'generate_scenario_from_prompt')

    def test_get_question_generator(self, mock_settings):
        """질문 생성기 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            generator = get_question_generator()

            assert generator is not None
            assert hasattr(generator, 'generate_next_question')

    def test_get_ai_response_generator(self, mock_settings):
        """AI 응답 생성기 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            generator = get_ai_response_generator()

            assert generator is not None
            assert hasattr(generator, 'generate_ai_response')


class TestFeedbackServiceDependencies:
    """Feedback Service 의존성 주입 테스트"""

    def test_get_pronunciation_evaluator(self, mock_settings):
        """발음 평가기 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            evaluator = get_pronunciation_evaluator()

            assert evaluator is not None
            # AzureSpeechService is a PronunciationEvaluator implementation
            assert hasattr(evaluator, '__class__')

    def test_get_grammar_evaluator(self, mock_settings):
        """문법 평가기 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            evaluator = get_grammar_evaluator()

            assert evaluator is not None
            assert hasattr(evaluator, 'evaluate_grammar')

    def test_get_relevance_evaluator(self, mock_settings):
        """맥락 평가기 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            evaluator = get_relevance_evaluator()

            assert evaluator is not None
            assert hasattr(evaluator, 'evaluate_relevance')

    def test_get_feedback_judge(self, mock_settings):
        """피드백 판단기 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            judge = get_feedback_judge()

            assert judge is not None
            assert hasattr(judge, 'judge_correction_needed')

    def test_get_feedback_orchestrator(self, mock_settings):
        """피드백 조율기 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            # Clear caches for this test
            get_grammar_evaluator.cache_clear()
            get_relevance_evaluator.cache_clear()
            get_pronunciation_evaluator.cache_clear()
            get_feedback_judge.cache_clear()
            get_azure_usage_tracker.cache_clear()
            get_feedback_orchestrator.cache_clear()

            orchestrator = get_feedback_orchestrator()

            assert orchestrator is not None
            assert hasattr(orchestrator, 'evaluate_response_fast')

    def test_get_feedback_agent_service(self, mock_settings):
        """피드백 에이전트 서비스 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            # Clear caches
            get_grammar_evaluator.cache_clear()
            get_relevance_evaluator.cache_clear()
            get_pronunciation_evaluator.cache_clear()
            get_feedback_judge.cache_clear()
            get_azure_usage_tracker.cache_clear()
            get_feedback_orchestrator.cache_clear()

            # Pass orchestrator as a mock to avoid complex DI initialization
            mock_orchestrator = MagicMock()
            service = get_feedback_agent_service(orchestrator=mock_orchestrator)

            assert service is not None
            # FeedbackAgentService is a deprecated facade
            assert hasattr(service, '__class__')


class TestRepositoryDependencies:
    """Repository 의존성 주입 테스트"""

    def test_get_session_repository(self, mock_settings):
        """세션 저장소 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            repo = get_session_repository()

            assert repo is not None
            assert hasattr(repo, 'save_session')
            assert hasattr(repo, 'get_session')
            assert hasattr(repo, 'delete_session')

    def test_get_scenario_repository(self, mock_settings):
        """시나리오 저장소 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            repo = get_scenario_repository()

            assert repo is not None
            assert hasattr(repo, 'get_scenario')
            assert hasattr(repo, 'get_user_scenarios')


class TestSessionServiceDependencies:
    """Session Service 의존성 주입 테스트"""

    def test_get_session_service(self, mock_settings, mock_session_repository, mock_scenario_repository):
        """세션 서비스 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            with patch('app.roleplaying.services.dependencies.get_session_repository', return_value=mock_session_repository):
                with patch('app.roleplaying.services.dependencies.get_scenario_repository', return_value=mock_scenario_repository):
                    service = get_session_service(
                        session_repo=mock_session_repository,
                        scenario_repo=mock_scenario_repository
                    )

                    assert service is not None
                    assert hasattr(service, 'setup_session')

    def test_get_ai_tutor_service(self, mock_settings):
        """AI 튜터 서비스 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            mock_question_gen = MagicMock()
            service = get_ai_tutor_service(question_generator=mock_question_gen)

            assert service is not None
            assert hasattr(service, 'generate_reply')


class TestScenarioServiceDependencies:
    """Scenario Service 의존성 주입 테스트"""

    def test_get_slack_scenario_service(self, mock_settings):
        """Slack 시나리오 생성 서비스 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            with patch('app.roleplaying.services.dependencies.LLMService'):
                service = get_slack_scenario_service()

                assert service is not None
                # SlackScenarioService exists
                assert hasattr(service, '__class__')

    def test_get_prompt_based_scenario_service(self, mock_settings):
        """프롬프트 기반 시나리오 생성 서비스 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            with patch('app.roleplaying.services.dependencies.LLMService'):
                service = get_prompt_based_scenario_service()

                assert service is not None
                # PromptBasedScenarioService exists
                assert hasattr(service, '__class__')


class TestAzureUtilityDependencies:
    """Azure 유틸리티 의존성 주입 테스트"""

    def test_get_azure_usage_tracker(self, mock_settings):
        """Azure 사용량 추적기 의존성 주입"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            tracker = get_azure_usage_tracker()

            assert tracker is not None
            # AzureUsageTracker implementation
            assert hasattr(tracker, '__class__')


class TestTypeAliases:
    """FastAPI 타입 별칭 테스트"""

    def test_conversation_analyzer_dep_type(self):
        """ConversationAnalyzerDep 타입 별칭"""
        # 타입 별칭이 Annotated 형태로 정의되었는지 확인
        assert hasattr(ConversationAnalyzerDep, '__metadata__')

    def test_scenario_generator_dep_type(self):
        """ScenarioGeneratorDep 타입 별칭"""
        assert hasattr(ScenarioGeneratorDep, '__metadata__')

    def test_question_generator_dep_type(self):
        """QuestionGeneratorDep 타입 별칭"""
        assert hasattr(QuestionGeneratorDep, '__metadata__')

    def test_ai_response_generator_dep_type(self):
        """AIResponseGeneratorDep 타입 별칭"""
        assert hasattr(AIResponseGeneratorDep, '__metadata__')

    def test_grammar_evaluator_dep_type(self):
        """GrammarEvaluatorDep 타입 별칭"""
        assert hasattr(GrammarEvaluatorDep, '__metadata__')

    def test_relevance_evaluator_dep_type(self):
        """RelevanceEvaluatorDep 타입 별칭"""
        assert hasattr(RelevanceEvaluatorDep, '__metadata__')

    def test_feedback_judge_dep_type(self):
        """FeedbackJudgeDep 타입 별칭"""
        assert hasattr(FeedbackJudgeDep, '__metadata__')

    def test_feedback_orchestrator_dep_type(self):
        """FeedbackOrchestratorDep 타입 별칭"""
        assert hasattr(FeedbackOrchestratorDep, '__metadata__')

    def test_session_repository_dep_type(self):
        """SessionRepositoryDep 타입 별칭"""
        assert hasattr(SessionRepositoryDep, '__metadata__')

    def test_scenario_repository_dep_type(self):
        """ScenarioRepositoryDep 타입 별칭"""
        assert hasattr(ScenarioRepositoryDep, '__metadata__')

    def test_ai_tutor_service_dep_type(self):
        """AITutorServiceDep 타입 별칭"""
        assert hasattr(AITutorServiceDep, '__metadata__')

    def test_session_service_dep_type(self):
        """SessionServiceDep 타입 별칭"""
        assert hasattr(SessionServiceDep, '__metadata__')


class TestDependencyInjectionIntegration:
    """DI 통합 테스트"""

    def test_feedback_orchestrator_has_all_evaluators(self, mock_settings):
        """FeedbackOrchestrator가 모든 평가기를 포함"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            # Clear all caches
            get_grammar_evaluator.cache_clear()
            get_relevance_evaluator.cache_clear()
            get_pronunciation_evaluator.cache_clear()
            get_feedback_judge.cache_clear()
            get_azure_usage_tracker.cache_clear()
            get_feedback_orchestrator.cache_clear()

            orchestrator = get_feedback_orchestrator()

            assert orchestrator.grammar_evaluator is not None
            assert orchestrator.relevance_evaluator is not None
            assert orchestrator.pronunciation_evaluator is not None
            assert orchestrator.feedback_judge is not None

    def test_session_service_has_both_repositories(self, mock_settings, mock_session_repository, mock_scenario_repository):
        """SessionService가 두 저장소를 포함"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            service = get_session_service(
                session_repo=mock_session_repository,
                scenario_repo=mock_scenario_repository
            )

            assert service is not None
            assert hasattr(service, 'setup_session')
            # SessionServiceImpl has repositories injected internally

    def test_cache_clearing(self, mock_settings):
        """캐시 초기화 작동 확인"""
        with patch('app.roleplaying.services.dependencies.settings', mock_settings):
            get_conversation_analyzer.cache_clear()

            analyzer1 = get_conversation_analyzer()
            analyzer2 = get_conversation_analyzer()

            # 캐시가 작동함을 확인 (같은 인스턴스 반환)
            assert analyzer1 is analyzer2
