"""전체 시나리오 출력"""

import requests
import json

url = "http://localhost:8000/scenario/generate"

# Chapter 07 선택: Writing a Request Email
payload = {
    "user_id": 1,
    "topic": "요청 이메일 작성",
    "scenario_type": "business_email",
    "difficulty": "intermediate",
    "num_turns": 20,
    "chapter_filter": "Chapter 07: Writing a Request Email (요청 메일 작성하기)",
    "include_korean_hints": True,
    "save_to_db": False
}

print("=" * 100)
print("📧 시나리오 생성 결과 전체 보기")
print("=" * 100)
print(f"\n선택한 챕터: {payload['chapter_filter']}")
print(f"주제: {payload['topic']}")
print(f"유형: {payload['scenario_type']}")
print(f"난이도: {payload['difficulty']}")

try:
    print("\n⏳ 시나리오 생성 중... (약 30-60초 소요)")
    response = requests.post(url, json=payload, timeout=180)

    if response.status_code == 200:
        data = response.json()

        print("\n" + "=" * 100)
        print("✅ 시나리오 생성 완료!")
        print("=" * 100)

        print(f"\n📌 제목: {data['title']}")
        print(f"📝 설명: {data['description']}")
        print(f"\n🎭 상황 설명:")
        print(f"   {data['situation']}")
        print(f"\n👤 사용자 역할: {data['user_role']}")
        print(f"🤖 AI 역할: {data['ai_role']}")

        print(f"\n📚 참조 챕터:")
        for ch in data['source_chapters']:
            print(f"   ✓ {ch}")

        # 검증
        if len(data['source_chapters']) == 1:
            print("   ✅ 단일 챕터만 사용됨!")
        else:
            print(f"   ⚠️ 주의: {len(data['source_chapters'])}개 챕터 사용됨")

        dialogues = data['dialogues']
        ai_count = sum(1 for d in dialogues if d['speaker'] == 'AI')
        user_count = sum(1 for d in dialogues if d['speaker'] == 'User')

        print(f"\n📊 대화 통계:")
        print(f"   총 턴 수: {len(dialogues)}")
        print(f"   AI 턴: {ai_count}개")
        print(f"   User 턴: {user_count}개")

        if ai_count == 10 and user_count == 10:
            print("   ✅ AI 10개, User 10개 정확히 생성됨!")
        else:
            print(f"   ⚠️ 주의: 예상과 다른 턴 수")

        print("\n" + "=" * 100)
        print("💬 전체 대화 내용 (20턴)")
        print("=" * 100)

        for i, dialogue in enumerate(dialogues, 1):
            speaker_emoji = "🤖" if dialogue['speaker'] == 'AI' else "👤"
            speaker_label = "AI" if dialogue['speaker'] == 'AI' else "User"

            print(f"\n{'─' * 100}")
            print(f"{speaker_emoji} Turn {dialogue['turn_number']} ({speaker_label})")
            print(f"{'─' * 100}")
            print(f"영어: {dialogue['text']}")

            if dialogue.get('korean_hint'):
                print(f"\n힌트: {dialogue['korean_hint']}")

            if dialogue.get('key_expressions'):
                print(f"\n핵심 표현: {', '.join(dialogue['key_expressions'][:3])}")

        print("\n" + "=" * 100)
        print("🎯 학습 포인트")
        print("=" * 100)

        print(f"\n📌 핵심 표현 ({len(data['key_expressions'])}개):")
        for i, expr in enumerate(data['key_expressions'][:10], 1):
            print(f"   {i}. {expr}")
        if len(data['key_expressions']) > 10:
            print(f"   ... 외 {len(data['key_expressions']) - 10}개")

        print(f"\n📖 주요 어휘 ({len(data['vocabulary'])}개):")
        for i, vocab in enumerate(data['vocabulary'][:10], 1):
            print(f"   {i}. {vocab}")
        if len(data['vocabulary']) > 10:
            print(f"   ... 외 {len(data['vocabulary']) - 10}개")

        print(f"\n📚 문법 포인트 ({len(data['grammar_points'])}개):")
        for i, grammar in enumerate(data['grammar_points'], 1):
            print(f"   {i}. {grammar}")

        print("\n" + "=" * 100)
        print("✅ 시나리오 검증 완료!")
        print("=" * 100)

    else:
        print(f"\n❌ API 호출 실패: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
