#!/bin/bash

# Spring 2 API curl 테스트
# 이 스크립트는 curl로 Spring2 API를 테스트합니다.

SPRING2_URL="http://localhost:8081"
SESSION_ID="curl-test-$(date +%s)"

echo "========================================"
echo "Spring 2 API Curl Test"
echo "========================================"
echo ""
echo "Spring2 URL: $SPRING2_URL"
echo "Session ID: $SESSION_ID"
echo ""

# 더미 오디오 파일 생성 (1초 분량의 무음 PCM)
echo "Creating dummy audio file..."
dd if=/dev/zero bs=1 count=32000 of=/tmp/test_audio.wav 2>/dev/null
echo "✓ Audio file created: /tmp/test_audio.wav (32000 bytes)"
echo ""

# curl로 multipart/form-data 요청 전송
echo "========================================"
echo "Sending multipart/form-data request..."
echo "========================================"
echo ""

curl -v \
  -X POST "$SPRING2_URL/internal/sessions/$SESSION_ID/utterances" \
  -F "speaker=user" \
  -F "text=Hello, I am a backend developer" \
  -F "utterance_index=0" \
  -F "audio=@/tmp/test_audio.wav" \
  2>&1

echo ""
echo ""
echo "========================================"
echo "Test completed"
echo "========================================"