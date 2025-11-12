"""
Slack Client
============
Slack API 호출을 위한 HTTP 클라이언트.

역할:
    - Slack Web API와 통신 (requests 또는 httpx 사용)
    - 토큰 기반 인증 및 오류 처리
    - API Rate Limit 및 재시도 로직 내장

주요 함수:
    - get_users()
    - get_channels()
    - get_messages(channel_id)

의존성:
    - config.py (SLACK_API_TOKEN)
"""