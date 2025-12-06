"""
IT Chatbot Router
=================
IT 용어 설명 챗봇 REST API

Endpoints:
- POST /it-explanation/chatbot - IT 용어 설명 챗봇 대화
"""

import logging
from fastapi import APIRouter, HTTPException

from app.it_explanation.models.schemas import ChatbotMessage, ChatbotResponse
from app.it_explanation.services.chatbot_service import ChatbotService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/it-explanation", tags=["it-explanation"])

# 서비스 초기화
chatbot_service = ChatbotService()


@router.post("/chatbot", response_model=ChatbotResponse)
async def chat_with_bot(request: ChatbotMessage):
    """
    IT 용어 설명 챗봇

    사용자의 질문에 대해 쉽고 명확한 설명을 제공합니다.
    대화 히스토리를 포함하면 컨텍스트 기반 응답을 받을 수 있습니다.

    Args:
        request: ChatbotMessage
            - user_message: 사용자 질문
            - conversation_history: 대화 히스토리 (선택)
                [{"role": "user", "content": "..."},
                 {"role": "assistant", "content": "..."}]

    Returns:
        ChatbotResponse: 챗봇 응답
    """
    try:
        logger.info(f"💬 [API] POST /it-explanation/chatbot")
        logger.debug(f"User message: {request.user_message[:100]}...")

        # 챗봇 응답 생성
        response = await chatbot_service.get_response(
            user_message=request.user_message,
            conversation_history=request.conversation_history
        )

        # TODO: Spring 2에 대화 저장 (conversation_id 받아오기)
        mock_conversation_id = None

        return ChatbotResponse(
            bot_response=response,
            conversation_id=mock_conversation_id
        )

    except Exception as e:
        logger.error(f"Chatbot request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
