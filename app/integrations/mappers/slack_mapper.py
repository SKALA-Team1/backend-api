"""
Slack Mapper
============
Slack API 응답(JSON)을 내부 데이터 모델에 맞게 변환하는 모듈.

역할:
    - Slack 사용자, 메시지, 채널 데이터를 InternalUser, InternalMessage, InternalChannel 등으로 변환
    - 필드명 통일, 누락 필드 보정, timestamp 변환 등 처리

주요 함수:
    - map_user(slack_user)
    - map_channel(slack_channel)
    - map_message(slack_message)
"""