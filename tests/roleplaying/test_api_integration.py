"""
Test API Integration
====================

API 계층 통합 테스트:
- API 스키마 검증
- 세션 설정 요청/응답
- 시나리오 API 통신
"""

import pytest
from datetime import datetime, timedelta

from app.roleplaying.api.api_schemas import (
    InternalSessionSetupRequest,
    InternalSessionSetupResponse,
    PromptBasedScenarioRequestDto,
    PromptBasedScenarioResponseDto
)


class TestSessionSetupRequest:
    """세션 설정 요청 스키마 테스트"""

    def test_session_setup_request_valid(self):
        """유효한 세션 설정 요청"""
        request = InternalSessionSetupRequest(
            sessionId="session-123",
            userId=1,
            scenarioId=1
        )
        assert request.sessionId == "session-123"
        assert request.userId == 1
        assert request.scenarioId == 1

    def test_session_setup_request_invalid_user_id(self):
        """사용자 ID 검증"""
        with pytest.raises(Exception):  # Pydantic ValueError
            InternalSessionSetupRequest(
                sessionId="session-123",
                userId=0,  # 양수 필요
                scenarioId=1
            )

    def test_session_setup_response(self):
        """세션 설정 응답"""
        from app.roleplaying.api.api_schemas import ScenarioDetail

        scenario = ScenarioDetail(
            scenarioId=1,
            subjectId=1,
            myRole="Engineer",
            aiRole="Lead",
            title="Test",
            topicType="detail",
            fixedQuestions=["Q1", "Q2", "Q3"]
        )

        expires_at = datetime.now() + timedelta(hours=1)

        response = InternalSessionSetupResponse(
            sessionId="session-123",
            wsUrl="ws://localhost:8000/ws/roleplaying/session-123",
            scenario=scenario,
            expiresAt=expires_at
        )

        assert response.sessionId == "session-123"
        assert "session-123" in response.wsUrl
        assert response.scenario.scenarioId == 1


class TestPromptBasedScenarioRequest:
    """프롬프트 기반 시나리오 요청 테스트"""

    def test_prompt_scenario_request_valid(self):
        """유효한 프롬프트 시나리오 요청"""
        request = PromptBasedScenarioRequestDto(
            userId=1,
            myRole="Backend Engineer",
            aiRole="CTO",
            situation="Architecture design discussion"
        )
        assert request.userId == 1
        assert request.myRole == "Backend Engineer"
        assert request.aiRole == "CTO"

    def test_prompt_scenario_request_validation(self):
        """프롬프트 시나리오 요청 검증"""
        # 사용자 ID 검증
        with pytest.raises(Exception):
            PromptBasedScenarioRequestDto(
                userId=0,  # 양수 필요
                myRole="Engineer",
                aiRole="Lead",
                situation="Test"
            )

        # 역할 검증
        with pytest.raises(Exception):
            PromptBasedScenarioRequestDto(
                userId=1,
                myRole="",  # 빈 문자열 불가
                aiRole="Lead",
                situation="Test"
            )

        # 상황 검증
        with pytest.raises(Exception):
            PromptBasedScenarioRequestDto(
                userId=1,
                myRole="Engineer",
                aiRole="Lead",
                situation="a" * 501  # 500자 초과
            )


class TestAnalysisRequest:
    """Slack 시나리오 분석 요청 테스트"""

    def test_analysis_request_valid(self, sample_conversation_messages):
        """유효한 분석 요청"""
        from app.roleplaying.api.api_schemas import AnalysisRequestDto

        request = AnalysisRequestDto(
            userId=1,
            myRole="Engineer",
            conversationDate="2024-12-02",
            messages=sample_conversation_messages,
            aiRoles=["Tech Lead", "Project Manager", "QA Engineer"]
        )

        assert request.userId == 1
        assert len(request.messages) == 3
        assert len(request.aiRoles) == 3

    def test_analysis_request_empty_messages(self):
        """빈 메시지 목록 검증"""
        from app.roleplaying.api.api_schemas import AnalysisRequestDto

        # 빈 메시지는 나중에 라우터에서 검증됨
        request = AnalysisRequestDto(
            userId=1,
            myRole="Engineer",
            conversationDate="2024-12-02",
            messages=[],
            aiRoles=["Tech Lead"]
        )

        assert len(request.messages) == 0


class TestScenarioDetail:
    """시나리오 상세 정보 테스트"""

    def test_scenario_detail_valid(self, sample_scenario_detail_extended):
        """유효한 시나리오 상세 정보"""
        assert sample_scenario_detail_extended.scenarioId == 1
        assert sample_scenario_detail_extended.myRole == "Senior Backend Engineer"
        assert sample_scenario_detail_extended.aiRole == "CTO"
        assert len(sample_scenario_detail_extended.fixedQuestions) == 3

    def test_scenario_detail_topics(self):
        """시나리오 토픽 타입"""
        from app.roleplaying.api.api_schemas import ScenarioDetail

        scenarios = [
            {"topic": "overview", "type": "overview"},
            {"topic": "detail", "type": "detail"}
        ]

        for scenario in scenarios:
            detail = ScenarioDetail(
                scenarioId=1,
                subjectId=1,
                myRole="Engineer",
                aiRole="Lead",
                title="Test",
                topicType=scenario["type"],
                fixedQuestions=["Q1", "Q2", "Q3"]
            )
            assert detail.topicType == scenario["type"]
