"""
특정 세션 ID의 종합 피드백 조회
사용법: python check_feedback_by_session.py <session_id>
"""
import pymysql
import sys

if len(sys.argv) < 2:
    print("사용법: python check_feedback_by_session.py <session_id>")
    print("\n예시:")
    print("  python check_feedback_by_session.py 556c61fb-ba12-4d99-b61b-213b6007d28d")
    sys.exit(1)

session_id = sys.argv[1]

# DB 연결
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
        SELECT
            session_id,
            scenario_id,
            final_feedback_short,
            final_feedback_long,
            created_at
        FROM scenario_feedback
        WHERE session_id = %s
        """
        cursor.execute(sql, (session_id,))
        result = cursor.fetchone()

        if not result:
            print(f"❌ 세션 ID '{session_id}'의 종합 피드백이 DB에 없습니다.")
        else:
            session_id, scenario_id, short, long, created_at = result

            print(f"✅ 종합 피드백 발견!")
            print(f"\n{'='*80}")
            print(f"세션 ID: {session_id}")
            print(f"시나리오 ID: {scenario_id}")
            print(f"생성 시간: {created_at}")
            print(f"\n{'='*80}")
            print(f"📝 짧은 피드백:")
            print(f"{'='*80}")
            print(short)
            print(f"\n{'='*80}")
            print(f"📄 긴 피드백:")
            print(f"{'='*80}")
            print(long)

finally:
    conn.close()
