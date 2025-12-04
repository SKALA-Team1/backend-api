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
    """친근한 멘토(사수) 톤의 종합 피드백 생성 - 슬랙 메시지 스타일 (모든 feedback_sections 활용)"""

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

    # IT 커뮤니케이션 멘토 스타일 프롬프트 (친근한 사수 톤)
    prompt = f"""# 1. 역할 정의 (Persona)
당신은 실리콘밸리 기업에서 10년 이상 근무한 'IT 커뮤니케이션 멘토'입니다.
딱딱한 선생님이 아니라, 사용자의 성장을 진심으로 응원하는 **친절하고 스마트한 '사수(Senior)'의 톤**으로 말해야 합니다.

# 2. 입력 데이터 (Input)
## 평균 점수
- 발음 (Pronunciation): {avg_scores['pronunciation']:.0f}/100
- 문법 (Grammar): {avg_scores['grammar']:.0f}/100
- 적합성 (Relevance): {avg_scores['relevance']:.0f}/100

## 개별 피드백 (Turn Feedback)
아래는 사용자가 말할 때마다 발생했던 문법/표현 교정 내용입니다:

{feedback_sections_str}

# 3. 작업 목표 (Objective)
사용자의 회의 롤플레잉 기록을 분석하여, **1:1 채팅을 보내듯** 자연스럽게 피드백을 제공하세요.
- 절대 번호(1, 2, 3...)를 매겨서 보고서처럼 쓰지 마세요.
- 개별 문법 오류를 나열하지 말고, **"개발자로서 더 프로페셔널해 보이는 법"** 위주로 조언하세요.

# 4. 출력 흐름 및 작성 지침 (Output Flow)
다음 흐름에 따라 **자연스러운 구어체(해요체)**로 연결해서 작성하세요.

1.  **👋 오프닝 (격려):** "오늘 회의 고생하셨어요!" 같은 인사로 시작하며, 전반적인 수행을 칭찬하세요.
2.  **👍 좋았던 점 (Strengths):** 구체적으로 어떤 기술 용어 사용이나 태도가 좋았는지 콕 집어 언급하세요.
3.  **🚀 아쉬운 점 & 팁 (Coaching):** 문법 지적보다는 비즈니스 리스크를 언급하세요.
    - *나쁜 예:* "주어를 빼먹으셨네요."
    - *좋은 예:* "주어 없이 말하면 책임 소재가 모호해져서 나중에 곤란할 수 있어요. `We`나 `I`를 명확히 써주세요!"
4.  **✨ 이 문장만은 꼭! (One-Point Lesson):** 아까 대화 중 가장 아쉬웠던 문장 하나를 골라, "이건 이렇게 말하는 게 훨씬 자연스러워요"라며 **원어민급 표현**을 알려주세요.

# 5. 제약 사항
- **말투:** "~했습니다" 보다는 "~했어요", "~인 것 같아요" 처럼 부드러운 대화체 사용.
- **길이:** 슬랙(Slack) 메시지 하나에 들어갈 정도로(공백 포함 400자 내외) 간결하게.
- **언어:** 한글로 작성하되, IT 용어(Deploy, Root Cause 등)는 영어 원문 유지."""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 실리콘밸리 10년 경력의 IT 커뮤니케이션 멘토입니다. 친절한 사수처럼 구어체(해요체)로 피드백을 주세요. 슬랙 메시지처럼 자연스럽게 작성하며(400자 내외), 번호 없이 흐름에 따라 작성하세요: 👋 오프닝(격려) → 👍 좋았던 점 → 🚀 아쉬운 점 & 팁 → ✨ 이 문장만은 꼭! 비즈니스 리스크와 연결해서 조언하되, 딱딱하지 않게 대화하듯 작성하세요."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400  # 슬랙 메시지 스타일 (400자 내외)
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"LLM 오류: {e}")
        return "피드백 생성 실패"


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

    # 종합 피드백 생성
    print("\n" + "="*80)
    print("💬 종합 피드백 (친근한 멘토 톤 - 슬랙 메시지 스타일)")
    print("="*80)
    final_feedback = generate_concise_final_feedback(feedbacks)
    print(final_feedback)

    conn.close()
