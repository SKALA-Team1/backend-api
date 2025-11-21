"""
통합 WebSocket 테스트 스크립트
==============================
1) REST API로 롤플레잉 세션을 생성하고
2) 응답에 포함된 WebSocket URL 및 fixedQuestions를 사용하여
   WebSocket 흐름을 실제 클라이언트처럼 테스트한다.

Usage:
    python scripts/test_websocket_with_session.py <user_id> <scenario_id>
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict

import httpx
import websockets

FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8082")


async def create_session(user_id: int, scenario_id: int) -> Dict[str, Any]:
    """REST API를 호출하여 세션을 생성하고 세션 정보를 반환"""
    async with httpx.AsyncClient(base_url=FASTAPI_BASE_URL, timeout=15.0) as client:
        response = await client.post(
            "/roleplaying/sessions",
            json={"userId": user_id, "scenarioId": scenario_id}
        )
        response.raise_for_status()
        return response.json()


async def run_websocket_flow(user_id: int, payload: Dict[str, Any]) -> None:
    """세션 정보를 사용하여 WebSocket 시나리오를 실행"""
    ws_url = payload["ws_url"]
    scenario = payload["scenario"]

    print(f"✅ Session created: {payload['session_id']}")
    print(f"🔗 WebSocket URL: {ws_url}")
    print(f"🎯 Scenario: {scenario['title']}")

    init_message = {
        "type": "INIT",
        "userId": user_id,
        "subjectId": scenario["subjectId"],
        "myRole": scenario["myRole"],
        "aiRole": scenario["aiRole"],
        "fixedQuestions": scenario["fixedQuestions"],
    }

    async with websockets.connect(ws_url) as websocket:
        await websocket.send(json.dumps(init_message))
        print("📤 INIT sent with DB-sourced fixedQuestions")

        for _ in range(2):  # ACK + 첫 질문
            message = await websocket.recv()
            print(f"📥 {message}")

        # 테스트 완료 후 세션 종료
        await websocket.send(json.dumps({"type": "END_SESSION"}))
        end_event = await websocket.recv()
        print(f"📥 {end_event}")


async def main(user_id: int, scenario_id: int) -> None:
    payload = await create_session(user_id, scenario_id)
    await run_websocket_flow(user_id, payload)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/test_websocket_with_session.py <user_id> <scenario_id>")
        sys.exit(1)

    asyncio.run(main(int(sys.argv[1]), int(sys.argv[2])))
