"""
종합 피드백 생성 테스트 스크립트 (임시)
"""
import asyncio
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.feedback.services.aggregation_service import generate_comprehensive_feedback


async def test_comprehensive_feedback(session_id: str):
    """종합 피드백 생성 테스트"""

    # DB 연결
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print(f"\n{'='*60}")
        print(f"🧪 종합 피드백 생성 테스트 시작")
        print(f"📋 Session ID: {session_id}")
        print(f"{'='*60}\n")

        # 종합 피드백 생성
        result = await generate_comprehensive_feedback(session_id, db)

        if result:
            print(f"\n{'='*60}")
            print(f"✅ 종합 피드백 생성 성공!")
            print(f"{'='*60}\n")

            print(f"📊 평균 점수:")
            print(f"  - 발음: {result.get('total_pronunciation')}/100")
            print(f"  - 문법: {result.get('total_grammar')}/100")
            print(f"  - 다양성: {result.get('total_diversity')}/100")

            print(f"\n📝 짧은 피드백 ({len(result.get('feedback_short', ''))}자):")
            print(f"{'─'*60}")
            print(result.get('feedback_short'))

            print(f"\n📜 긴 피드백 ({len(result.get('feedback_long', ''))}자):")
            print(f"{'─'*60}")
            print(result.get('feedback_long'))

            print(f"\n{'='*60}")

        else:
            print("\n❌ 종합 피드백 생성 실패")

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    session_id = sys.argv[1] if len(sys.argv) > 1 else "3a812dab-a31d-4133-b89d-9c4495511053"
    asyncio.run(test_comprehensive_feedback(session_id))
