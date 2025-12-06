#!/usr/bin/env python3
"""
종합 피드백 생성 테스트 스크립트

사용법:
    python test_feedback_generation.py <session_id>
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.feedback.services.feedback_service import get_feedback_service


async def test_feedback_generation(session_id: str):
    """특정 세션의 종합 피드백 생성 테스트"""
    print(f"🔍 Testing feedback generation for session: {session_id}")
    print("=" * 60)

    try:
        # 피드백 서비스 가져오기
        feedback_service = get_feedback_service()

        # 피드백 생성
        print(f"\n🤖 Generating feedback...")
        result = await feedback_service.get_session_feedback(
            session_id=session_id,
            scenario_id=1  # 테스트용 시나리오 ID
        )

        # 결과 출력
        print(f"\n{'='*60}")
        print(f"📊 평균 점수:")
        print(f"  - 발음: {result.avg_pronunciation:.1f}/100")
        print(f"  - 문법: {result.avg_accuracy:.1f}/100")
        print(f"  - 적합성: {result.avg_fluency:.1f}/100")
        print(f"\n{'='*60}")
        print(f"📝 긴 피드백 (Long Feedback):")
        print(f"{'-'*60}")
        print(result.final_feedback_long)
        print(f"\n{'='*60}")
        print(f"💬 짧은 피드백 (Short Feedback):")
        print(f"{'-'*60}")
        print(result.final_feedback_short)
        print(f"\n{'='*60}")
        print(f"\n✅ 피드백 생성 완료!")

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python test_feedback_generation.py <session_id>")
        print("\n예시:")
        print("  python test_feedback_generation.py session-123-456")
        sys.exit(1)

    session_id = sys.argv[1]
    asyncio.run(test_feedback_generation(session_id))
