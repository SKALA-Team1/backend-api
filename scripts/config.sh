#!/bin/bash

##############################################################################
# Voice Roleplay 테스트 환경 설정
##############################################################################

# FastAPI 서버 설정
export FASTAPI_HOST="${FASTAPI_HOST:-0.0.0.0}"
export FASTAPI_PORT="${FASTAPI_PORT:-8082}"
export FASTAPI_URL="http://localhost:${FASTAPI_PORT}"

# 음성 녹음 설정
export RECORD_DURATION="${RECORD_DURATION:-5}"
export SAMPLE_RATE="${SAMPLE_RATE:-16000}"

# 로깅 설정
export VERBOSE="${VERBOSE:-false}"

# 타임아웃 설정
export SERVER_STARTUP_TIMEOUT="${SERVER_STARTUP_TIMEOUT:-30}"
export AI_RESPONSE_TIMEOUT="${AI_RESPONSE_TIMEOUT:-20}"

# 백엔드 디렉토리
export BACKEND_DIR="$(dirname "$(dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")")"
export SCRIPTS_DIR="$(dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")"

# Python 인터프리터
export PYTHON_BIN="${PYTHON_BIN:-python3}"

# 색상 정의
export GREEN='\033[0;32m'
export BLUE='\033[0;34m'
export YELLOW='\033[1;33m'
export RED='\033[0;31m'
export CYAN='\033[0;36m'
export NC='\033[0m'