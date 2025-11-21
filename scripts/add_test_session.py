"""
테스트용 세션 데이터를 Redis에 추가하는 스크립트

실행 방법:
    python scripts/add_test_session.py

결과:
    Redis에 세션 데이터가 저장됨
    - Key: session:test-session-123
    - TTL: 2 hours
"""

import json
import redis
from datetime import datetime, timedelta

# Redis 연결
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

# 테스트 세션 ID
session_id = "test-session-001"

# 세션 데이터 (Spring 1이 저장하는 형식)
session_data = {
    "userId": 1,
    "scenarioId": 1,
    "role": "user",
    "scenarioType": "ROLEPLAYING",
    "startedAt": datetime.utcnow().isoformat() + "Z",
    "expiresAt": (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
}

# Redis 키
redis_key = f"session:{session_id}"

# Redis에 저장 (TTL 2시간)
redis_client.setex(
    redis_key,
    7200,  # 2 hours in seconds
    json.dumps(session_data)
)

print(f"✅ 테스트 세션 생성 완료!")
print(f"   Session ID: {session_id}")
print(f"   Redis Key: {redis_key}")
print(f"   Data: {json.dumps(session_data, indent=2)}")
print(f"\n🔗 WebSocket URL:")
print(f"   ws://localhost:8000/ws/roleplaying/{session_id}")

# 검증
stored = redis_client.get(redis_key)
if stored:
    print(f"\n✓ Redis 저장 확인: {stored}")
else:
    print(f"\n✗ Redis 저장 실패")