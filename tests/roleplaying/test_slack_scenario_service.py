from datetime import datetime
import pytest

from app.roleplaying.schemas import SlackMessageDto, MessageRole
from app.roleplaying.services.slack_scenario_service import (
    SlackScenarioService,
    ConversationSummary
)


class StubLLMService:
    def __init__(self):
        self.summary_calls = []
        self.build_calls = []

    async def summarize_messages(self, messages, perspective):
        self.summary_calls.append((messages, perspective))
        return f"{perspective}-summary"

    async def build_fixed_questions(self, user_summary, counterpart_summary):
        self.build_calls.append((user_summary, counterpart_summary))
        return ["Q1", "Q2", "Q3"]


def test_slack_message_accepts_my_message_flag():
    timestamp = datetime.utcnow()
    msg_default = SlackMessageDto(
        timestamp=timestamp,
        senderName="User",
        text="Hello team"
    )
    assert msg_default.myMessage is False

    msg_true = SlackMessageDto(
        timestamp=timestamp,
        senderName="User",
        text="I own this message",
        myMessage=True
    )
    assert msg_true.myMessage is True


@pytest.mark.asyncio
async def test_build_conversation_summary_tracks_mine_flag():
    service = SlackScenarioService()
    stub_llm = StubLLMService()
    service.llm_service = stub_llm

    conversation = [
        MessageRole(content="내 메시지 1", sender="나", mine=True),
        MessageRole(content="상대 메시지 1", sender="동료", mine=False),
        MessageRole(content="내 메시지 2", sender="나", mine=True),
    ]

    summary = await service._build_conversation_summary(conversation)

    assert stub_llm.summary_calls == [
        (["내 메시지 1", "내 메시지 2"], "user"),
        (["상대 메시지 1"], "counterpart")
    ]
    assert summary.user_summary == "user-summary"
    assert summary.counterpart_summary == "counterpart-summary"


@pytest.mark.asyncio
async def test_generate_fixed_questions_includes_summaries_in_prompt():
    service = SlackScenarioService()
    stub_llm = StubLLMService()
    service.llm_service = stub_llm

    summary = ConversationSummary(
        my_messages=["내 메시지"],
        others_messages=["상대 메시지"],
        user_summary="사용자 이슈 요약",
        counterpart_summary="상대방 질문 요약"
    )

    questions = await service._generate_fixed_questions(
        summary=summary,
        my_role="Backend Engineer",
        situation="API performance outage",
        ai_role="Tech Lead",
        topic_type="detail",
        fallback_questions=["old1", "old2", "old3"]
    )

    assert questions == ["Q1", "Q2", "Q3"]
    assert "[AI role: Tech Lead]" in stub_llm.build_calls[0][0]
    assert "[AI role: Tech Lead]" in stub_llm.build_calls[0][1]


def test_format_title_removes_roles_and_limits_length():
    service = SlackScenarioService()

    formatted = service._format_title(
        title="Tech Lead Deep Dive | Backend Engineer Handoff Strategy",
        ai_role="Tech Lead",
        topic_type="detail",
        my_role="Backend Engineer"
    )

    assert "Tech Lead" not in formatted
    assert "Backend Engineer" not in formatted
    assert len(formatted) <= 50


def test_format_title_fallback_when_empty():
    service = SlackScenarioService()

    formatted = service._format_title(
        title="",
        ai_role="Project Manager",
        topic_type="overview",
        my_role="Data Analyst"
    )

    assert formatted == "Focused Overview"
