"""
Slack Sync Service
==================
Slack 데이터를 내부 DB와 동기화하는 기능을 담당합니다.

역할:
    - Slack API 호출 (SlackClient 이용)
    - 메시지, 유저, 채널 등 메타데이터 수집
    - Mapper와 Normalizer를 통해 데이터 정규화 후 저장

주요 함수:
    - sync_users()
    - sync_channels()
    - sync_messages()

의존성:
    - Clients/slack_client.py
    - Mappers/slack_mapper.py
    - Normalizers/text_cleaner.py
    - repository.py
"""