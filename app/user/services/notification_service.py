"""
Notification Service
====================
사용자의 알림 설정 및 발송 로직을 관리하는 서비스 모듈.

역할:
    - 이메일/앱 푸시/슬랙 등 알림 채널 통합 관리
    - 이벤트 트리거 기반 알림 발송
    - 알림 수신 설정 (Opt-in/out) 제어

주요 함수(예시):
    - send_notification(user_id, type, payload)
    - update_notification_preferences(user_id, prefs)
    - get_unread_notifications(user_id)

의존성:
    - repository.py
    - Core/email_sender.py
    - Integrations/Clients/slack_client.py (선택)
"""