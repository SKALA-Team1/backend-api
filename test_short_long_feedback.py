"""
종합 피드백 생성 테스트 (짧은/긴 버전)
FastAPI에 요청 → OpenAI 피드백 생성 → DB 저장 확인
"""
import requests
import json

# FastAPI URL
FASTAPI_URL = "http://localhost:8082"

# 테스트할 세션 ID (실제 존재하는 세션 사용)
SESSION_ID = "fc04bbd9-722d-470b-a5a2-29fa33e2877c"
SCENARIO_ID = 70

print("=" * 80)
print("종합 피드백 생성 테스트")
print("=" * 80)
print()

# 1. FastAPI에 종합 피드백 생성 요청
print("📤 FastAPI에 종합 피드백 생성 요청 중...")
url = f"{FASTAPI_URL}/feedback/session/{SESSION_ID}"
params = {"scenario_id": SCENARIO_ID}

try:
    response = requests.get(url, params=params, timeout=300)

    if response.status_code == 200:
        result = response.json()

        print("✅ 종합 피드백 생성 성공!\n")

        # 디버깅: 응답 데이터 확인
        print("DEBUG - 응답 키:", list(result.keys()))
        print()

        print("=" * 80)
        print("전체 세션 통합 분석")
        print("=" * 80)
        print()
        print(f"총 {result.get('total_turns', 0)}개의 턴 피드백")
        print()
        print("평균 점수:")
        print(f"  발음: {result.get('avg_pronunciation', 0.0)}")
        print(f"  문법: {result.get('avg_accuracy', 0.0)}")
        print(f"  적합성: {result.get('avg_completeness', 0.0)}")
        print()
        print("=" * 80)
        print(":speech_balloon: 종합 피드백")
        print("=" * 80)
        print()
        print(":memo: 짧은 버전 (1-2문장):")
        print("-" * 80)
        print(result.get("final_feedback_short", "N/A"))
        print()
        print("=" * 80)
        print(":book: 긴 버전 (7문장):")
        print("-" * 80)
        print(result.get("final_feedback_long", "N/A"))
        print()

        # 2. DB 저장 확인
        print("🔍 DB 저장 확인 중...")
        import pymysql

        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='9799',
            database='skuseme_db_2',
            charset='utf8mb4'
        )

        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT final_feedback_short, final_feedback_long
                FROM scenario_feedback
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """
                cursor.execute(sql, (SESSION_ID,))
                db_result = cursor.fetchone()

                if db_result:
                    print("✅ DB에 저장 확인됨!")
                else:
                    print("❌ DB에 저장되지 않음")
        finally:
            conn.close()

    else:
        print(f"❌ 요청 실패: {response.status_code}")
        print(f"응답: {response.text}")

except requests.exceptions.Timeout:
    print("❌ 타임아웃: OpenAI 응답이 300초를 초과했습니다.")
except Exception as e:
    print(f"❌ 에러 발생: {e}")

print()
print("=" * 80)
print("테스트 완료")
print("=" * 80)
