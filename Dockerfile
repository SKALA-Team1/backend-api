# Stage 1: Build
FROM python:3.11-slim AS builder

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /tmp/* /var/tmp/*

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Stage 1에서 설치한 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 소스 코드 복사
COPY . .

# 포트 노출
EXPOSE 8082

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8082/health')" || exit 1

# 애플리케이션 시작
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8082"]