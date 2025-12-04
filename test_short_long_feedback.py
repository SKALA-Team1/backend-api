"""
짧은 버전 + 긴 버전 피드백 테스트
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 테스트 데이터
avg_scores = {
    "avg_pronunciation": 75.0,
    "avg_accuracy": 80.0,
    "avg_fluency": 70.0,
    "overall_score": 75.0
}

feedback_sections_str = """[
  {
    "turn_index": 0,
    "message_text": "We have critical bug in production",
    "feedback_sections": [
      {"type": "grammar", "score": 70, "feedback_en": "Missing article 'a'"}
    ]
  }
]"""

print("=" * 80)
print("1️⃣  긴 버전 생성 테스트 (10-13문장)")
print("=" * 80)

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
각 섹션마다 아래 문장 수를 지켜서 충분히 상세하게 작성해주세요 (전체 7문장 이상).

1. **👋 오프닝 (1문장):** "오늘 회의 고생하셨어요!" 같은 간단한 인사말 한 문장.
2. **👍 좋았던 점 (3-4문장):** 구체적으로 어떤 기술 용어 사용이나 태도가 좋았는지 콕 집어 언급하세요. 칭찬을 충분히 자세하게.
3. **🚀 아쉬운 점 & 팁 (4-5문장):** 문법 지적보다는 비즈니스 리스크를 언급하세요. 왜 중요한지, 어떻게 개선할지 구체적으로.
    - *나쁜 예:* "주어를 빼먹으셨네요."
    - *좋은 예:* "주어 없이 말하면 책임 소재가 모호해져서 나중에 곤란할 수 있어요. `We`나 `I`를 명확히 써주세요!"
4. **✨ 이 문장만은 꼭! (2-3문장):** 아까 대화 중 가장 아쉬웠던 문장 하나를 골라, "이건 이렇게 말하는 게 훨씬 자연스러워요"라며 **원어민급 표현**을 알려주세요.

# 5. 제약 사항

- **말투:** "~했습니다" 보다는 "~했어요", "~인 것 같아요" 처럼 부드러운 대화체 사용.
- **길이:** 전체 10문장 이상 (섹션별 문장 수 준수)
- **언어:** 한글로 작성하되, IT 용어(Deploy, Root Cause 등)는 영어 원문 유지."""

long_response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {
            "role": "system",
            "content": "당신은 실리콘밸리 10년 경력의 IT 커뮤니케이션 멘토입니다. 친절한 사수처럼 구어체(해요체)로 피드백을 주세요. 반드시 다음 구조를 지켜서 작성하세요:\n\n👋 오프닝: 1문장\n👍 좋았던 점: 3-4문장 (구체적 칭찬)\n🚀 아쉬운 점 & 팁: 4-5문장 (비즈니스 리스크 연결)\n✨ 이 문장만은 꼭: 2-3문장 (구체적 예시)\n\n총 10-13문장으로 작성하세요. 각 섹션을 충분히 자세하게 작성하여 전체 길이를 채우세요. 번호 없이 자연스럽게 흐름에 따라 대화하듯 작성하세요."
        },
        {"role": "user", "content": long_prompt}
    ],
    temperature=0.7,
    max_tokens=1200
)

long_feedback = long_response.choices[0].message.content.strip()
print(long_feedback)
print(f"\n문장 수: {long_feedback.count('.')}")

print("\n" + "=" * 80)
print("2️⃣  짧은 버전 생성 테스트 (1-2문장)")
print("=" * 80)

short_prompt = f"""사용자의 영어 회의 롤플레잉 결과를 1-2문장으로 요약해주세요.

평균 점수:
- 발음: {avg_scores['avg_pronunciation']:.1f}점
- 문법: {avg_scores['avg_accuracy']:.1f}점
- 적합성: {avg_scores['avg_fluency']:.1f}점
- 종합: {avg_scores['overall_score']:.1f}점

요구사항:
- 친근한 멘토 톤 (해요체)
- 1-2문장으로 간결하게
- 가장 강조하고 싶은 핵심만 전달
- IT 실무자 관점에서 조언

예시: "오늘 회의 수고하셨어요! 전반적으로 좋았지만, 문장 구조를 좀 더 명확하게 하면 글로벌 팀과 소통할 때 훨씬 자신감 생길 거예요."
"""

short_response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {
            "role": "system",
            "content": "당신은 실리콘밸리 IT 커뮤니케이션 멘토입니다. 친절한 사수처럼 1-2문장으로 핵심만 전달하세요."
        },
        {"role": "user", "content": short_prompt}
    ],
    temperature=0.7,
    max_tokens=200
)

short_feedback = short_response.choices[0].message.content.strip()
print(short_feedback)
print(f"\n문장 수: {short_feedback.count('.')}")

print("\n" + "=" * 80)
print("3️⃣  최종 결과 (dict 형태)")
print("=" * 80)

result = {
    "short": short_feedback,
    "long": long_feedback
}

print(f"short: {result['short']}")
print(f"\nlong: {result['long']}")

print("\n✅ 테스트 완료!")
