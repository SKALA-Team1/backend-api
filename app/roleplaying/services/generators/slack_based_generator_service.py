"""
Slack-Based Generator Service
=============================
Slack 메시지 로그를 기반으로 롤플레잉 시나리오를 구성하는 Generator 모듈.

역할:
    - Slack 대화 내용에서 주제, 감정, 인물 관계를 추출하여 시나리오화
    - 실제 협업 데이터나 피드백 내용을 활용한 시뮬레이션 대화 생성

주요 함수:
    - generate_from_slack(channel_id)
    - extract_roles(messages)
    - summarize_conversation_context()

의존성:
    - Integrations/Clients/slack_client.py
    - Integrations/Mappers/slack_mapper.py
    - summarizer.py
"""