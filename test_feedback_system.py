"""
실시간 피드백 시스템 테스트 스크립트
"""
import asyncio
import json
from datetime import datetime, timezone

# ============================================
# 1. 서비스 임포트 테스트
# ============================================

def test_imports():
    """필요한 모듈 임포트 테스트"""
    print("\n📦 [1단계] 모듈 임포트 테스트")
    try:
        from app.roleplaying.services.azure_speech_service import azure_speech_service
        print("✅ azure_speech_service 임포트 성공")

        from app.roleplaying.services.feedback_agent_service import feedback_agent_service
        print("✅ feedback_agent_service 임포트 성공")

        from app.roleplaying.services.azure_usage_tracker import usage_tracker
        print("✅ azure_usage_tracker 임포트 성공")

        return True
    except Exception as e:
        print(f"❌ 임포트 실패: {e}")
        return False


# ============================================
# 2. 환경 설정 테스트
# ============================================

def test_config():
    """환경 설정 테스트"""
    print("\n⚙️  [2단계] 환경 설정 테스트")
    try:
        from app.config import settings

        print(f"✅ AZURE_SPEECH_KEY: {settings.AZURE_SPEECH_KEY[:20]}...")
        print(f"✅ AZURE_SPEECH_REGION: {settings.AZURE_SPEECH_REGION}")
        print(f"✅ ROLEPLAY_MAX_TURNS: {settings.ROLEPLAY_MAX_TURNS}")
        print(f"✅ FEEDBACK_LLM_PROVIDER: {settings.FEEDBACK_LLM_PROVIDER}")
        print(f"✅ OLLAMA_BASE_URL: {settings.OLLAMA_BASE_URL}")
        print(f"✅ FEEDBACK_MAX_RETRY_PER_QUESTION: {settings.FEEDBACK_MAX_RETRY_PER_QUESTION}")

        return True
    except Exception as e:
        print(f"❌ 설정 로드 실패: {e}")
        return False


# ============================================
# 3. Redis 연결 테스트
# ============================================

async def test_redis():
    """Redis 연결 테스트"""
    print("\n🔴 [3단계] Redis 연결 테스트")
    try:
        from app.roleplaying.services.azure_usage_tracker import usage_tracker

        await usage_tracker.init()

        if usage_tracker.initialized:
            usage = await usage_tracker.get_today_usage()
            remaining = await usage_tracker.get_remaining()
            percentage = await usage_tracker.get_usage_percentage()

            print(f"✅ Redis 연결 성공")
            print(f"   오늘 사용: {usage}/600")
            print(f"   남은 횟수: {remaining}")
            print(f"   사용률: {percentage:.1f}%")

            await usage_tracker.close()
            return True
        else:
            print("❌ Redis 초기화 실패")
            return False
    except Exception as e:
        print(f"❌ Redis 연결 실패: {e}")
        print("   → Redis를 실행했는지 확인하세요: redis-cli ping")
        return False


# ============================================
# 4. 피드백 평가 테스트 (Ollama 필요)
# ============================================

async def test_feedback_evaluation():
    """피드백 평가 테스트"""
    print("\n🧠 [4단계] 피드백 평가 테스트 (Ollama 필요)")
    try:
        from app.roleplaying.services.feedback_agent_service import feedback_agent_service

        # 테스트 데이터
        user_text = "I like playing tennis because it keeps me fit"
        conversation_history = []
        scenario_context = {
            "my_role": "Student",
            "ai_role": "Tutor",
            "current_question": "What is your favorite hobby?"
        }

        print(f"   테스트 문장: '{user_text}'")
        print("   평가 실행 중...")

        feedback_result = await feedback_agent_service.evaluate_response_fast(
            user_text=user_text,
            audio_data=None,
            conversation_history=conversation_history,
            scenario_context=scenario_context,
            retry_count=0
        )

        print("✅ 피드백 평가 완료")
        print(f"   발음: {feedback_result['scores']['pronunciation_score']}")
        print(f"   문법: {feedback_result['scores']['grammar_score']}")
        print(f"   맥락: {feedback_result['scores']['relevance_score']}")
        print(f"   종합: {feedback_result['scores']['overall_score']}")
        print(f"   교정 필요: {feedback_result['needs_correction']}")
        print(f"   피드백: {feedback_result['feedback_text'][:100]}...")

        return True
    except Exception as e:
        print(f"❌ 피드백 평가 실패: {e}")
        print("   → Ollama를 실행했는지 확인하세요: ollama run llama2")
        return False


# ============================================
# 5. SessionState 테스트
# ============================================

def test_session_state():
    """SessionState 테스트"""
    print("\n📋 [5단계] SessionState 테스트")
    try:
        from app.roleplaying.session_manager import SessionState
        from datetime import datetime, timezone, timedelta

        # SessionState 생성
        session = SessionState(
            session_id="test-session-001",
            user_id=123,
            subject_id=1,
            my_role="Student",
            ai_role="English Teacher",
            fixed_questions=["How are you?", "What's your name?", "Where are you from?"],
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )

        print(f"✅ SessionState 생성 성공")
        print(f"   세션 ID: {session.session_id}")
        print(f"   사용자 역할: {session.my_role}")
        print(f"   AI 역할: {session.ai_role}")
        print(f"   최대 재시도: {session.max_retry_per_question}")

        # 재시도 로직 테스트
        print(f"   재시도 가능: {session.can_retry()}")
        session.increment_retry_count()
        print(f"   1회 재시도 후: retry_count={session.current_question_retry_count}")
        session.reset_retry_count()
        print(f"   리셋 후: retry_count={session.current_question_retry_count}")

        return True
    except Exception as e:
        print(f"❌ SessionState 테스트 실패: {e}")
        return False


# ============================================
# 6. WebSocket 메시지 모델 테스트
# ============================================

def test_websocket_messages():
    """WebSocket 메시지 모델 테스트"""
    print("\n📨 [6단계] WebSocket 메시지 모델 테스트")
    try:
        from app.roleplaying.ws_models import (
            FeedbackMessage,
            FeedbackStreamingMessage,
            RetryRequiredMessage
        )

        # FeedbackMessage
        feedback_msg = FeedbackMessage(
            pronunciation_score=88,
            grammar_score=92,
            relevance_score=90,
            overall_score=90
        )
        print(f"✅ FeedbackMessage: {feedback_msg.model_dump()}")

        # FeedbackStreamingMessage
        streaming_msg = FeedbackStreamingMessage(
            chunk="발음이 명확하고 문법도 정확합니다."
        )
        print(f"✅ FeedbackStreamingMessage: {streaming_msg.model_dump()}")

        # RetryRequiredMessage
        retry_msg = RetryRequiredMessage(
            reason="grammar",
            retry_count=1,
            max_retries=3
        )
        print(f"✅ RetryRequiredMessage: {retry_msg.model_dump()}")

        return True
    except Exception as e:
        print(f"❌ WebSocket 메시지 테스트 실패: {e}")
        return False


# ============================================
# 메인 테스트 함수
# ============================================

async def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("🚀 실시간 피드백 시스템 테스트 시작")
    print("=" * 60)

    results = {
        "모듈 임포트": test_imports(),
        "환경 설정": test_config(),
        "SessionState": test_session_state(),
        "WebSocket 메시지": test_websocket_messages(),
        "Redis 연결": await test_redis(),
        "피드백 평가": await test_feedback_evaluation(),
    }

    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{test_name}: {status}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\n총 {passed}/{total} 성공")

    if passed == total:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️  일부 테스트 실패. 위의 에러 메시지를 확인하세요.")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
