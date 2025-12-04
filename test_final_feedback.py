"""
종합 피드백 생성 테스트 스크립트

scenario_message 테이블의 feedback_sections를 활용하여
친근한 사수(멘토) 톤의 종합 피드백을 생성합니다.
(슬랙 메시지 스타일, 구어체, 400자 내외)
"""

import pymysql
import json
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# DB 연결
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='9799',
    database='skuseme_db_2',
    port=3306
)

# OpenAI 클라이언트
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_session_feedbacks(session_id: str):
    """세션의 모든 피드백 메시지 가져오기"""
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            message_id, turn_index, message_text,
            pronunciation_score, grammar_score, relevance_score, overall_score,
            feedback_sections, needs_correction, primary_issue
        FROM scenario_message
        WHERE session_id = %s AND speaker = 'user' AND feedback_sections IS NOT NULL
        ORDER BY turn_index
    ''', (session_id,))

    results = cursor.fetchall()
    cursor.close()

    feedbacks = []
    for row in results:
        feedback_sections = json.loads(row[7]) if row[7] else []
        feedbacks.append({
            'turn_index': row[1],
            'message_text': row[2],
            'pronunciation_score': row[3],
            'grammar_score': row[4],
            'relevance_score': row[5],
            'overall_score': row[6],
            'feedback_sections': feedback_sections,
            'needs_correction': row[8],
            'primary_issue': row[9]
        })

    return feedbacks

def extract_key_issues(feedbacks):
    """피드백에서 핵심 이슈 추출 (간결하게)"""
    issues = {
        'pronunciation': [],
        'grammar': [],
        'relevance': []
    }

    for fb in feedbacks:
        sections = fb['feedback_sections']
        turn = fb['turn_index']

        for section in sections:
            section_type = section['type']
            score = section.get('score')
            feedback_text = section.get('feedback_en', '')

            if section_type == 'pronunciation' and score and score < 80:
                issues['pronunciation'].append({
                    'turn': turn,
                    'score': score,
                    'issue': feedback_text[:100]  # 짧게
                })
            elif section_type == 'grammar' and score and score < 90:
                issues['grammar'].append({
                    'turn': turn,
                    'score': score,
                    'issue': feedback_text[:100]  # 짧게
                })
            elif section_type == 'relevance' and score and score < 70:
                issues['relevance'].append({
                    'turn': turn,
                    'score': score,
                    'issue': feedback_text[:100]  # 짧게
                })

    return issues

def calculate_avg_scores(feedbacks):
    """평균 점수 계산"""
    total = len(feedbacks)
    if total == 0:
        return {}

    avg = {
        'pronunciation': 0,
        'grammar': 0,
        'relevance': 0,
        'overall': 0
    }

    for fb in feedbacks:
        avg['pronunciation'] += fb['pronunciation_score'] or 0
        avg['grammar'] += fb['grammar_score'] or 0
        avg['relevance'] += fb['relevance_score'] or 0
        avg['overall'] += fb['overall_score'] or 0

    for key in avg:
        avg[key] = round(avg[key] / total, 1)

    return avg

def generate_concise_final_feedback(feedbacks):
    """친근한 멘토(사수) 톤의 종합 피드백 생성 - 짧은 버전(1-2문장) + 긴 버전(7문장)"""

    # 평균 점수 계산
    avg_scores = calculate_avg_scores(feedbacks)

    # 모든 feedback_sections를 LLM에 전달 (필터링 없이)
    all_feedback_data = []
    for fb in feedbacks:
        turn_data = {
            'turn_index': fb['turn_index'],
            'message_text': fb['message_text'],
            'feedback_sections': fb['feedback_sections']
        }
        all_feedback_data.append(turn_data)

    # JSON 형태로 포맷팅
    feedback_sections_str = json.dumps(all_feedback_data, ensure_ascii=False, indent=2)

    # ========== 1. 긴 버전 생성 (7문장) ==========
    long_prompt = f"""# 1. 역할 정의 (Persona)
당신은 실리콘밸리 기업에서 10년 이상 근무한 'IT 커뮤니케이션 멘토'입니다.
딱딱한 선생님이 아니라, 사용자의 성장을 진심으로 응원하는 **친절하고 스마트한 '사수(Senior)'의 톤**으로 말해야 합니다.

# 2. 입력 데이터 (Input)

1. 대화 로그(Log): 사용자와 AI의 전체 회의 내용
2. 개별 피드백(Turn Feedback): 문법 및 표현 교정 내역

{feedback_sections_str}

# 3. 작업 목표 (Objective)

사용자의 회의 롤플레잉 기록을 분석하여, **1:1 채팅을 보내듯** 자연스럽게 피드백을 제공하세요.

- 절대 번호(1, 2, 3...)를 매겨서 보고서처럼 쓰지 마세요.
- 개별 문법 오류를 나열하지 말고, **"개발자로서 더 프로페셔널해 보이는 법"** 위주로 조언하세요.

# 4. 출력 흐름 및 작성 지침 (Output Flow)

다음 흐름에 따라 **자연스러운 구어체(해요체)**로 연결해서 작성하세요.
각 섹션마다 아래 문장 수를 지켜서 충분히 상세하게 작성해주세요 (전체 7문장).

1. **👋 오프닝 (1문장):** "오늘 회의 고생하셨어요!" 같은 간단한 인사말 한 문장.
2. **👍 좋았던 점 (2-3문장):** 구체적으로 어떤 기술 용어 사용이나 태도가 좋았는지 콕 집어 언급하세요. 칭찬을 충분히 자세하게.
3. **🚀 아쉬운 점 & 팁 (2-3문장):** 문법 지적보다는 비즈니스 리스크를 언급하세요. 왜 중요한지, 어떻게 개선할지 구체적으로.
    - *나쁜 예:* "주어를 빼먹으셨네요."
    - *좋은 예:* "주어 없이 말하면 책임 소재가 모호해져서 나중에 곤란할 수 있어요. `We`나 `I`를 명확히 써주세요!"
4. **✨ 이 문장만은 꼭! (1-2문장):** 아까 대화 중 가장 아쉬웠던 문장 하나를 골라, "이건 이렇게 말하는 게 훨씬 자연스러워요"라며 **원어민급 표현**을 알려주세요.
    - **중요:** 영어 예시 문장을 제공할 때는 반드시 한글 번역을 괄호 안에 함께 제공하세요.
    - 예: "We need to monitor the cache hit rate." (캐시 적중률을 모니터링해야 합니다.)

# 5. 제약 사항

- **말투:** "~했습니다" 보다는 "~했어요", "~인 것 같아요" 처럼 부드러운 대화체 사용.
- **길이:** 전체 7문장 (섹션별 문장 수 준수)
- **언어:** 한글로 작성하되, IT 용어(Deploy, Root Cause 등)는 영어 원문 유지."""

    try:
        long_response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 실리콘밸리 10년 경력의 IT 커뮤니케이션 멘토입니다. 친절한 사수처럼 구어체(해요체)로 피드백을 주세요. 반드시 다음 구조를 지켜서 작성하세요:\n\n👋 오프닝: 1문장\n👍 좋았던 점: 2-3문장 (구체적 칭찬)\n🚀 아쉬운 점 & 팁: 2-3문장 (비즈니스 리스크 연결)\n✨ 이 문장만은 꼭: 1-2문장 (구체적 예시)\n\n총 7문장으로 작성하세요. 각 섹션을 충분히 자세하게 작성하여 전체 길이를 채우세요. 번호 없이 자연스럽게 흐름에 따라 대화하듯 작성하세요.\n\n**중요:** 영어 예시 문장을 제공할 때는 반드시 한글 번역을 괄호 안에 함께 제공하세요. 예: \"We need to monitor the cache hit rate.\" (캐시 적중률을 모니터링해야 합니다.)"
                },
                {"role": "user", "content": long_prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )

        long_feedback = long_response.choices[0].message.content.strip()

        # ========== 2. 짧은 버전 생성 (긴 버전을 요약) ==========
        short_prompt = f"""아래의 긴 피드백을 1-2문장으로 요약해주세요.

긴 피드백:
{long_feedback}

요구사항:
- 친근한 멘토 톤 (해요체)
- 인사말, 칭찬 부분은 생략
- 아쉬운 점과 개선 방법만 1-2문장으로 핵심만 추출
- IT 실무자 관점에서 가장 중요한 조언만
- **중요:** 긴 피드백의 논리와 맥락을 유지하세요. 긴 버전에서 긍정적으로 언급한 부분을 부정적으로 바꾸지 마세요.

예시: "답변이 간결한 건 좋지만, 구체적인 수치나 방법까지 함께 설명하면 팀원들이 바로 실행에 옮길 수 있어요."
예시: "주어와 목적을 명확히 쓰는 연습을 하면 회의에서 책임 소재를 분명하게 전달할 수 있어요."
"""

        short_response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 실리콘밸리 IT 커뮤니케이션 멘토입니다. 주어진 긴 피드백에서 핵심 개선점만 1-2문장으로 추출하세요. 인사말, 칭찬은 생략하되, 긴 피드백의 논리와 맥락을 왜곡하지 마세요. 긴 버전에서 긍정적으로 언급한 부분은 부정적으로 바꾸지 말고, 전체적인 뉘앙스를 유지하면서 개선점만 간결하게 전달하세요."
                },
                {"role": "user", "content": short_prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )

        short_feedback = short_response.choices[0].message.content.strip()

        # ========== 3. dict로 반환 ==========
        return {
            "short": short_feedback,
            "long": long_feedback
        }

    except Exception as e:
        print(f"LLM 오류: {e}")
        return {
            "short": "피드백 생성 실패",
            "long": "피드백 생성 실패"
        }


# 메인 실행
if __name__ == "__main__":
    # 모든 세션의 모든 피드백 가져오기 (세션 구분 없이)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            message_id, turn_index, message_text,
            pronunciation_score, grammar_score, relevance_score, overall_score,
            feedback_sections, needs_correction, primary_issue
        FROM scenario_message
        WHERE speaker = 'user' AND feedback_sections IS NOT NULL
        ORDER BY created_at, turn_index
    ''')

    results = cursor.fetchall()
    if not results:
        print("피드백 데이터가 없습니다.")
        conn.close()
        exit()

    feedbacks = []
    for row in results:
        feedback_sections = json.loads(row[7]) if row[7] else []
        feedbacks.append({
            'turn_index': row[1],
            'message_text': row[2],
            'pronunciation_score': row[3],
            'grammar_score': row[4],
            'relevance_score': row[5],
            'overall_score': row[6],
            'feedback_sections': feedback_sections,
            'needs_correction': row[8],
            'primary_issue': row[9]
        })

    print(f"전체 세션 통합 분석")
    print("="*80)
    print(f"\n총 {len(feedbacks)}개의 턴 피드백")

    # 평균 점수
    avg_scores = calculate_avg_scores(feedbacks)
    print(f"\n평균 점수:")
    print(f"  발음: {avg_scores['pronunciation']}")
    print(f"  문법: {avg_scores['grammar']}")
    print(f"  적합성: {avg_scores['relevance']}")

    # 종합 피드백 생성 (짧은 버전 + 긴 버전)
    print("\n" + "="*80)
    print("💬 종합 피드백")
    print("="*80)
    feedback_result = generate_concise_final_feedback(feedbacks)

    print("\n📝 짧은 버전 (1-2문장):")
    print("-" * 80)
    print(feedback_result["short"])

    print("\n" + "="*80)
    print("📖 긴 버전 (7문장):")
    print("-" * 80)
    print(feedback_result["long"])

    conn.close()
