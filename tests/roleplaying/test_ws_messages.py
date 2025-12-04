"""
Test WebSocket Message Models
==============================

WebSocket 메시지 모델 테스트:
- 인바운드 메시지 (INIT, AUDIO_CHUNK, UTTERANCE_END, USER_TEXT, END_SESSION)
- 아웃바운드 메시지 (AI_TEXT, FEEDBACK, ERROR, SESSION_ENDED 등)
"""

import pytest
from app.roleplaying.handlers.ws_message_models import (
    InitMessage, AudioChunkMessage, UtteranceEndMessage,
    UserTextMessage, EndSessionMessage,
    AiTextMessage, AiTextStreamingMessage, FeedbackMessage,
    FeedbackStreamingMessage, RetryRequiredMessage,
    SessionEndedMessage, ErrorMessage, SttFinalMessage,
    get_fixed_question_index, FIXED_QUESTION_TURNS
)


class TestInboundMessages:
    """인바운드 메시지 (Client → FastAPI) 테스트"""

    def test_init_message_valid(self, sample_init_message):
        """INIT 메시지 생성"""
        assert sample_init_message.type == "INIT"
        assert sample_init_message.userId == 1
        assert sample_init_message.subjectId == 1
        assert sample_init_message.myRole == "Software Engineer"
        assert sample_init_message.aiRole == "Tech Lead"
        assert len(sample_init_message.fixedQuestions) == 3

    def test_init_message_validation_questions_count(self):
        """INIT 메시지: 고정 질문 개수 검증"""
        with pytest.raises(ValueError):
            InitMessage(
                type="INIT",
                userId=1,
                subjectId=1,
                myRole="Engineer",
                aiRole="Lead",
                fixedQuestions=["Q1", "Q2"]  # 2개만
            )

    def test_utterance_end_message(self):
        """UTTERANCE_END 메시지"""
        msg = UtteranceEndMessage(type="UTTERANCE_END")
        assert msg.type == "UTTERANCE_END"

    def test_user_text_message(self):
        """USER_TEXT 메시지"""
        msg = UserTextMessage(
            type="USER_TEXT",
            text="Hello, I need help with this"
        )
        assert msg.type == "USER_TEXT"
        assert msg.text == "Hello, I need help with this"

    def test_user_text_message_validation(self):
        """USER_TEXT 메시지: 빈 텍스트 검증"""
        with pytest.raises(ValueError):
            UserTextMessage(type="USER_TEXT", text="")

    def test_end_session_message(self):
        """END_SESSION 메시지"""
        msg = EndSessionMessage(type="END_SESSION")
        assert msg.type == "END_SESSION"


class TestOutboundMessages:
    """아웃바운드 메시지 (FastAPI → Client) 테스트"""

    def test_ai_text_message(self, sample_ai_text_message):
        """AI_TEXT 메시지"""
        assert sample_ai_text_message.type == "AI_TEXT"
        assert sample_ai_text_message.text == "This is an AI response"
        assert sample_ai_text_message.is_fixed_question is False

    def test_ai_text_streaming_message(self):
        """AI_TEXT_STREAMING 메시지"""
        msg = AiTextStreamingMessage(
            type="AI_TEXT_STREAMING",
            chunk="Hello",
            is_fixed_question=False
        )
        assert msg.type == "AI_TEXT_STREAMING"
        assert msg.chunk == "Hello"

    def test_feedback_message(self):
        """FEEDBACK 메시지"""
        msg = FeedbackMessage(
            type="FEEDBACK",
            pronunciation_score=85,
            grammar_score=90,
            relevance_score=88,
            overall_score=87
        )
        assert msg.type == "FEEDBACK"
        assert msg.pronunciation_score == 85
        assert msg.overall_score == 87

    def test_feedback_message_validation(self):
        """FEEDBACK 메시지: 점수 범위 검증"""
        with pytest.raises(ValueError):
            FeedbackMessage(
                type="FEEDBACK",
                pronunciation_score=150,  # 범위 초과
                grammar_score=90,
                relevance_score=88,
                overall_score=87
            )

    def test_feedback_streaming_message(self):
        """FEEDBACK_STREAMING 메시지"""
        msg = FeedbackStreamingMessage(
            type="FEEDBACK_STREAMING",
            chunk="Try saying it like this:"
        )
        assert msg.type == "FEEDBACK_STREAMING"
        assert msg.chunk == "Try saying it like this:"

    def test_retry_required_message(self):
        """RETRY_REQUIRED 메시지"""
        msg = RetryRequiredMessage(
            type="RETRY_REQUIRED",
            reason="pronunciation",
            retry_count=1,
            max_retries=3
        )
        assert msg.type == "RETRY_REQUIRED"
        assert msg.reason == "pronunciation"
        assert msg.retry_count == 1

    def test_session_ended_message(self):
        """SESSION_ENDED 메시지"""
        msg = SessionEndedMessage(
            type="SESSION_ENDED",
            reason="user_end"
        )
        assert msg.type == "SESSION_ENDED"
        assert msg.reason == "user_end"

    def test_session_ended_reasons(self):
        """SESSION_ENDED 종료 사유"""
        reasons = ["user_end", "timeout", "disconnected", "error", "turn_limit"]
        for reason in reasons:
            msg = SessionEndedMessage(type="SESSION_ENDED", reason=reason)
            assert msg.reason == reason

    def test_error_message(self):
        """ERROR 메시지"""
        msg = ErrorMessage(
            type="ERROR",
            message="STT failed",
            code="STT_001"
        )
        assert msg.type == "ERROR"
        assert msg.message == "STT failed"
        assert msg.code == "STT_001"

    def test_stt_final_message(self):
        """STT_FINAL 메시지"""
        msg = SttFinalMessage(
            type="STT_FINAL",
            text="Final transcription"
        )
        assert msg.type == "STT_FINAL"
        assert msg.text == "Final transcription"


class TestFixedQuestionMapping:
    """고정 질문 매핑 테스트"""

    def test_fixed_question_turns(self):
        """고정 질문 턴 상수"""
        assert FIXED_QUESTION_TURNS == {1: 0, 4: 1, 7: 2}

    def test_get_fixed_question_index_turn_1(self):
        """턴 1: 인덱스 0"""
        assert get_fixed_question_index(1) == 0

    def test_get_fixed_question_index_turn_4(self):
        """턴 4: 인덱스 1"""
        assert get_fixed_question_index(4) == 1

    def test_get_fixed_question_index_turn_7(self):
        """턴 7: 인덱스 2"""
        assert get_fixed_question_index(7) == 2

    def test_get_fixed_question_index_dynamic(self):
        """동적 질문 턴: None"""
        for turn in [2, 3, 5, 6, 8, 9, 10]:
            assert get_fixed_question_index(turn) is None


class TestMessageValidation:
    """메시지 검증 테스트"""

    def test_init_message_empty_role(self):
        """INIT 메시지: 빈 역할 검증"""
        with pytest.raises(ValueError):
            InitMessage(
                type="INIT",
                userId=1,
                subjectId=1,
                myRole="",
                aiRole="Lead",
                fixedQuestions=["Q1", "Q2", "Q3"]
            )

    def test_init_message_invalid_user_id(self):
        """INIT 메시지: 잘못된 사용자 ID"""
        with pytest.raises(ValueError):
            InitMessage(
                type="INIT",
                userId=0,  # 양수 필요
                subjectId=1,
                myRole="Engineer",
                aiRole="Lead",
                fixedQuestions=["Q1", "Q2", "Q3"]
            )

    def test_feedback_score_boundaries(self):
        """FEEDBACK 점수 경계값"""
        # 최소값
        msg = FeedbackMessage(
            type="FEEDBACK",
            pronunciation_score=0,
            grammar_score=0,
            relevance_score=0,
            overall_score=0
        )
        assert msg.pronunciation_score == 0

        # 최대값
        msg = FeedbackMessage(
            type="FEEDBACK",
            pronunciation_score=100,
            grammar_score=100,
            relevance_score=100,
            overall_score=100
        )
        assert msg.pronunciation_score == 100
