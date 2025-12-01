"""특정 챕터 시나리오 생성 테스트"""

import requests
import json

url = "http://localhost:8000/scenario/generate"

# Chapter 02 선택: Conducting Weekly Meetings
payload = {
    "user_id": 1,
    "topic": "주간 미팅 진행",
    "scenario_type": "meeting",
    "difficulty": "intermediate",
    "num_turns": 20,
    "chapter_filter": "Chapter 02: Conducting Weekly Meetings (주간미팅 진행하기)",
    "include_korean_hints": True,
    "save_to_db": False
}

print("=" * 80)
print("🎯 특정 챕터 기반 시나리오 생성 테스트")
print("=" * 80)
print(f"\n선택한 챕터: {payload['chapter_filter']}")
print(f"주제: {payload['topic']}")

try:
    print("\n⏳ API 호출 중...")
    response = requests.post(url, json=payload, timeout=120)

    if response.status_code == 200:
        data = response.json()

        print("\n" + "=" * 80)
        print("✅ 시나리오 생성 성공!")
        print("=" * 80)
        print(f"제목: {data['title']}")
        print(f"설명: {data['description']}")
        print(f"\n📚 참조 챕터:")
        for ch in data['source_chapters']:
            print(f"  - {ch}")

        # 챕터가 하나만 있는지 검증
        if len(data['source_chapters']) == 1:
            print("\n✅ 검증 성공: 단일 챕터만 사용됨!")
        else:
            print(f"\n❌ 검증 실패: {len(data['source_chapters'])}개 챕터 사용됨")

        print(f"\n총 턴 수: {len(data['dialogues'])}")
        ai_count = sum(1 for d in data['dialogues'] if d['speaker'] == 'AI')
        user_count = sum(1 for d in data['dialogues'] if d['speaker'] == 'User')
        print(f"AI 턴: {ai_count}개")
        print(f"User 턴: {user_count}개")

        print("\n첫 3턴:")
        for dialogue in data['dialogues'][:3]:
            speaker_emoji = "🤖" if dialogue['speaker'] == 'AI' else "👤"
            print(f"\n{speaker_emoji} Turn {dialogue['turn_number']} ({dialogue['speaker']}):")
            print(f"   {dialogue['text'][:100]}...")

    else:
        print(f"\n❌ API 호출 실패: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
