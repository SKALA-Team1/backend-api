"""
Spring2 final feedback API 테스트
실제 OpenAI로 생성한 피드백이 DB에 저장되는지 확인
"""
import requests
import json

# Spring2 API URL (직접 호출)
SPRING2_URL = "http://localhost:8081"

# 테스트할 세션 ID (실제 존재하는 세션 ID 사용)
SESSION_ID = "556c61fb-ba12-4d99-b61b-213b6007d28d"

# 1. 짧은/긴 피드백 생성 (실제 내용)
final_feedback_short = "답변이 간결한 건 좋지만, 구체적인 수치나 방법까지 함께 설명하면 팀원들이 바로 실행에 옮길 수 있어요."

final_feedback_long = """오늘 회의 고생하셨어요! 기술적인 단어를 정확히 사용하려는 태도가 정말 좋았고, caching이나 performance 같은 주제를 자신 있게 다룬 점이 인상적이었어요. 간결하게 핵심을 전달하려는 시도도 실무에서 분명 도움이 될 거예요.

다만, 답변이 너무 짧거나 구체적인 예시가 빠지면 팀원들이 실제로 무엇을 해야 할지 혼란스러울 수 있어요. 특히 시스템 성능이나 모니터링 관련해서는 어떤 지표를 볼지, 어떤 도구를 쓸지 명확히 말해주면 책임 소재가 분명해지고 대응도 쉬워져요. 커뮤니케이션 미스를 줄이려면 조금만 더 구체적으로 설명하는 습관을 들이면 좋을 것 같아요.

예를 들어, "To avoid inconsistent user experiences." 대신 "We need to monitor the cache hit rate and set up alerts for latency spikes to ensure consistent user experience." (캐시 적중률을 모니터링하고 지연 시간 급증에 대한 알림을 설정해야 사용자 경험의 일관성을 유지할 수 있습니다.)처럼 구체적인 액션까지 포함하면 훨씬 프로페셔널하게 들려요!"""

# 2. Spring2 API 호출
payload = {
    "finalFeedbackShort": final_feedback_short,
    "finalFeedbackLong": final_feedback_long,
    "avgPronunciationScore": 75.5,
    "avgAccuracyScore": 71.7,
    "avgFluencyScore": 30.0
}

print("=" * 80)
print("Spring2 API 호출 중...")
print("=" * 80)
print(f"URL: {SPRING2_URL}/internal/sessions/{SESSION_ID}/final-feedback")
print(f"\n요청 데이터:")
print(f"  짧은 피드백: {final_feedback_short[:50]}...")
print(f"  긴 피드백: {final_feedback_long[:50]}...")
print(f"  평균 점수: 발음={payload['avgPronunciationScore']}, 문법={payload['avgAccuracyScore']}, 적합성={payload['avgFluencyScore']}")

try:
    response = requests.post(
        f"{SPRING2_URL}/internal/sessions/{SESSION_ID}/final-feedback",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    print(f"\n응답 상태 코드: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ 성공!")
        print(f"응답: {json.dumps(result, indent=2, ensure_ascii=False)}")

        # 3. DB에서 확인
        print("\n" + "=" * 80)
        print("DB에서 저장된 데이터 확인 중...")
        print("=" * 80)

        import pymysql
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='9799',
            database='skuseme_db_2',
            port=3306,
            charset='utf8mb4'
        )

        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                feedback_id,
                final_feedback_short,
                final_feedback_long,
                total_pronunciation,
                total_grammar,
                total_diversity,
                total_score,
                created_at
            FROM scenario_feedback
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (SESSION_ID,))

        row = cursor.fetchone()
        if row:
            print(f"\n📊 DB 저장 확인:")
            print(f"  Feedback ID: {row[0]}")
            print(f"\n  📝 짧은 피드백:")
            print(f"     {row[1]}")
            print(f"\n  📖 긴 피드백:")
            print(f"     {row[2][:200]}...")
            print(f"\n  점수:")
            print(f"     발음: {row[3]}")
            print(f"     문법: {row[4]}")
            print(f"     적합성: {row[5]}")
            print(f"     종합: {row[6]}")
            print(f"  생성 시간: {row[7]}")
            print(f"\n✅ DB 저장 확인 완료!")
        else:
            print("❌ DB에서 데이터를 찾을 수 없습니다.")

        conn.close()

    else:
        print(f"❌ 실패: {response.text}")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
