"""
DB에 저장된 종합 피드백 확인
"""
import pymysql
from datetime import datetime

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
        # 최근 종합 피드백 5개 조회
        sql = """
        SELECT
            session_id,
            scenario_id,
            final_feedback_short,
            final_feedback_long,
            created_at
        FROM scenario_feedback
        ORDER BY created_at DESC
        LIMIT 5
        """
        cursor.execute(sql)
        results = cursor.fetchall()

        if not results:
            print("❌ DB에 저장된 종합 피드백이 없습니다.")
        else:
            print(f"✅ DB에 {len(results)}개의 종합 피드백이 있습니다.\n")

            for i, row in enumerate(results, 1):
                session_id, scenario_id, short, long, created_at = row

                print(f"{'='*80}")
                print(f"[{i}] 세션 ID: {session_id}")
                print(f"    시나리오 ID: {scenario_id}")
                print(f"    생성 시간: {created_at}")
                print(f"\n📝 짧은 피드백:")
                print(f"    {short}")
                print(f"\n📄 긴 피드백:")
                # 긴 피드백은 첫 300자만 출력
                if long:
                    long_preview = long[:300] + "..." if len(long) > 300 else long
                    print(f"    {long_preview}")
                else:
                    print("    (없음)")
                print()

finally:
    conn.close()
