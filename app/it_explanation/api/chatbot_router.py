"""
IT Chatbot Router
=================
IT 용어 설명 챗봇 REST API

Endpoints:
- POST /it-explanation/chatbot - IT 용어 설명 챗봇 대화
"""

import httpx
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.it_explanation.models.schemas import ChatbotMessage, ChatbotResponse
from app.it_explanation.services.chatbot_service import ChatbotService
from app.integrations.clients.spring2_client import spring2_client

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

        # current_question을 dict로 변환
        current_question_dict = None
        if request.current_question:
            current_question_dict = request.current_question.model_dump()

        # 챗봇 응답 생성
        response = await chatbot_service.get_response(
            user_message=request.user_message,
            conversation_history=request.conversation_history,
            current_question=current_question_dict
        )

        # Spring 2에 대화 저장
        conversation_id = None
        try:
            result = await spring2_client.save_chatbot_conversation(
                user_id=request.user_id,
                user_message=request.user_message,
                bot_response=response,
                context=None  # TODO: conversation_history를 JSON으로 변환하여 저장 (선택사항)
            )
            conversation_id = result.get("conversationId")
            logger.info(f"✅ Saved conversation to CRUD2: conversation_id={conversation_id}")
        except (httpx.RequestError, httpx.HTTPStatusError) as save_error:
            logger.error(f"⚠️ Failed to save conversation to CRUD2: {save_error}")
            # 저장 실패해도 챗봇 응답은 반환 (저장은 부가 기능)

        return ChatbotResponse(
            bot_response=response,
            conversation_id=conversation_id
        )

    except Exception as e:
        logger.error(f"Chatbot request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chatbot/stream")
async def chat_with_bot_stream(request: ChatbotMessage):
    """
    IT 용어 설명 챗봇 (스트리밍)

    사용자의 질문에 대해 토큰 단위로 실시간 스트리밍 응답을 제공합니다.
    대화 히스토리를 포함하면 컨텍스트 기반 응답을 받을 수 있습니다.

    Args:
        request: ChatbotMessage
            - user_message: 사용자 질문
            - conversation_history: 대화 히스토리 (선택)
            - current_question: 현재 연습 중인 질문 컨텍스트 (선택)

    Returns:
        StreamingResponse: 토큰 단위 스트리밍 응답
    """
    try:
        logger.info(f"💬 [API] POST /it-explanation/chatbot/stream")
        logger.debug(f"User message: {request.user_message[:100]}...")
        logger.debug(f"Request data - user_id: {request.user_id}, history: {len(request.conversation_history) if request.conversation_history else 0}, has_question: {request.current_question is not None}")

        # current_question을 dict로 변환
        current_question_dict = None
        if request.current_question:
            current_question_dict = request.current_question.model_dump()

        # 스트리밍 생성기
        async def generate_stream():
            full_response = ""
            try:
                async for token in chatbot_service.get_response_stream(
                    user_message=request.user_message,
                    conversation_history=request.conversation_history,
                    current_question=current_question_dict
                ):
                    full_response += token
                    yield token

                # 스트리밍 완료 후 Spring 2에 저장
                try:
                    await spring2_client.save_chatbot_conversation(
                        user_id=request.user_id,
                        user_message=request.user_message,
                        bot_response=full_response,
                        context=None
                    )
                    logger.info(f"✅ Saved streaming conversation to CRUD2")
                except (httpx.RequestError, httpx.HTTPStatusError) as save_error:
                    logger.error(f"⚠️ Failed to save streaming conversation to CRUD2: {save_error}")

            except Exception as e:
                logger.error(f"Chatbot streaming failed: {e}", exc_info=True)
                yield "죄송합니다. 오류가 발생했습니다. 다시 시도해 주세요."

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain; charset=utf-8"
        )

    except Exception as e:
        logger.error(f"Chatbot streaming request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
