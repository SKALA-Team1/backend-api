.PHONY: help server test test-mic test-verbose install-deps check-deps

# 기본 포트
FASTAPI_PORT := 8082
SPRING2_PORT := 8081

# 기본값
USER_ID := 1
SCENARIO_ID := 1
RECORD_DURATION := 3

help:
	@echo ""
	@echo "╔════════════════════════════════════════════════╗"
	@echo "║  SKALA 음성 롤플레잉 Makefile                 ║"
	@echo "╚════════════════════════════════════════════════╝"
	@echo ""
	@echo "📖 사용법:"
	@echo ""
	@echo "서버 관련:"
	@echo "  make server              FastAPI 서버 시작 (포트 8082)"
	@echo ""
	@echo "테스트 (더미 오디오):"
	@echo "  make test                기본 설정으로 테스트"
	@echo "  make test-verbose        상세 로깅 활성화"
	@echo ""
	@echo "테스트 (실제 마이크):"
	@echo "  make test-mic            마이크로 3초 녹음하여 테스트"
	@echo "  make test-mic-5          마이크로 5초 녹음하여 테스트"
	@echo "  make test-mic-verbose    마이크 + 상세 로깅"
	@echo ""
	@echo "커스텀 테스트:"
	@echo "  make test-custom USER_ID=2 SCENARIO_ID=5"
	@echo "  make test-mic-custom USER_ID=2 RECORD_DURATION=5"
	@echo ""
	@echo "의존성:"
	@echo "  make install-deps        필수 라이브러리 설치"
	@echo "  make check-deps          의존성 확인"
	@echo ""

# FastAPI 서버 시작
server:
	@echo ""
	@echo "🚀 FastAPI 서버 시작 (포트 $(FASTAPI_PORT))"
	@echo ""
	bash scripts/start_server.sh

# 필수 라이브러리 설치
install-deps:
	@echo ""
	@echo "📦 필수 라이브러리 설치"
	@echo ""
	pip install sounddevice soundfile websockets httpx

# 의존성 확인
check-deps:
	@echo ""
	@echo "✅ 의존성 확인 중..."
	@echo ""
	@python -c "import sounddevice; print('  ✓ sounddevice')" 2>/dev/null || echo "  ✗ sounddevice (필요)"
	@python -c "import soundfile; print('  ✓ soundfile')" 2>/dev/null || echo "  ✗ soundfile (필요)"
	@python -c "import websockets; print('  ✓ websockets')" 2>/dev/null || echo "  ✓ websockets (필요)"
	@python -c "import httpx; print('  ✓ httpx')" 2>/dev/null || echo "  ✗ httpx (필요)"
	@echo ""

# 기본 테스트 (더미 오디오)
test:
	@bash scripts/setup_and_test.sh --user-id $(USER_ID) --scenario-id $(SCENARIO_ID)

# 상세 로깅 테스트 (더미 오디오)
test-verbose:
	@bash scripts/setup_and_test.sh --user-id $(USER_ID) --scenario-id $(SCENARIO_ID) --verbose

# 마이크 테스트 (3초)
test-mic:
	@bash scripts/setup_and_test.sh --use-mic --record-duration 3

# 마이크 테스트 (5초)
test-mic-5:
	@bash scripts/setup_and_test.sh --use-mic --record-duration 5

# 마이크 상세 로깅 테스트
test-mic-verbose:
	@bash scripts/setup_and_test.sh --use-mic --record-duration 3 --verbose

# 커스텀 더미 오디오 테스트
test-custom:
	@bash scripts/setup_and_test.sh --user-id $(USER_ID) --scenario-id $(SCENARIO_ID)

# 커스텀 마이크 테스트
test-mic-custom:
	@bash scripts/setup_and_test.sh --use-mic --user-id $(USER_ID) --scenario-id $(SCENARIO_ID) --record-duration $(RECORD_DURATION)

.DEFAULT_GOAL := help
