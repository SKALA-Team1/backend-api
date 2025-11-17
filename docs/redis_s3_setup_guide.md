# Redis & S3 구성 가이드

## 📋 개요

SKALA 프로젝트에서 필요한 Redis와 S3 설정 방법을 안내합니다.

**용도:**
- **Redis:** WebSocket 세션 검증 (session_id 저장/조회)
- **S3:** 사용자 발화 오디오 파일 저장

---

## 🎯 구성 옵션 비교

| 옵션 | Redis | S3 | 비용 | 난이도 | 추천 환경 |
|------|-------|----|----|-------|----------|
| **Option 1: 로컬 개발** | Docker 로컬 | MinIO (S3 호환) | 무료 | ⭐ 쉬움 | 개발 |
| **Option 2: 클라우드 Free Tier** | Redis Cloud | AWS S3 Free | 거의 무료 | ⭐⭐ 중간 | 개발/테스트 |
| **Option 3: AWS 전체** | ElastiCache | AWS S3 | 유료 | ⭐⭐⭐ 어려움 | 프로덕션 |
| **Option 4: Docker Compose** | Redis Container | MinIO Container | 무료 | ⭐⭐ 중간 | 개발/테스트 |

---

## ✅ 권장: Option 4 - Docker Compose (개발 환경)

**장점:**
- ✅ 한 번에 Redis + MinIO 실행
- ✅ 팀원 간 환경 통일
- ✅ 설정 간단 (YAML 파일만)
- ✅ 무료
- ✅ 프로덕션 전환 쉬움 (환경 변수만 변경)

**단점:**
- ❌ Docker 필요
- ❌ 로컬 리소스 사용

---

## 🐳 Option 4: Docker Compose 설정 (권장)

### Step 1: docker-compose.yml 생성

프로젝트 루트에 `docker-compose.dev.yml` 파일 생성:

```yaml
version: '3.8'

services:
  # Redis (세션 저장소)
  redis:
    image: redis:7-alpine
    container_name: skala-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    networks:
      - skala-network

  # MinIO (S3 호환 오브젝트 스토리지)
  minio:
    image: minio/minio:latest
    container_name: skala-minio
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    volumes:
      - minio-data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 3s
      retries: 3
    networks:
      - skala-network

  # MinIO Client (버킷 자동 생성)
  minio-init:
    image: minio/mc:latest
    container_name: skala-minio-init
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set myminio http://minio:9000 minioadmin minioadmin123;
      mc mb --ignore-existing myminio/skala;
      mc anonymous set download myminio/skala;
      echo 'MinIO bucket created: skala';
      "
    networks:
      - skala-network

volumes:
  redis-data:
  minio-data:

networks:
  skala-network:
    driver: bridge
```

### Step 2: 실행

```bash
# 백그라운드 실행
docker-compose -f docker-compose.dev.yml up -d

# 로그 확인
docker-compose -f docker-compose.dev.yml logs -f

# 상태 확인
docker-compose -f docker-compose.dev.yml ps
```

**출력 예시:**
```
NAME                IMAGE               STATUS
skala-redis         redis:7-alpine      Up (healthy)
skala-minio         minio/minio         Up (healthy)
```

### Step 3: 접속 확인

#### Redis 테스트
```bash
# Redis CLI 접속
docker exec -it skala-redis redis-cli

# 명령어 테스트
127.0.0.1:6379> SET test "hello"
OK
127.0.0.1:6379> GET test
"hello"
127.0.0.1:6379> DEL test
(integer) 1
127.0.0.1:6379> exit
```

#### MinIO 테스트

1. **웹 콘솔 접속:**
   - URL: http://localhost:9001
   - Username: `minioadmin`
   - Password: `minioadmin123`

2. **버킷 확인:**
   - `skala` 버킷 자동 생성되어 있음

3. **파일 업로드 테스트:**
   ```bash
   # 더미 파일 생성
   echo "test audio data" > test.wav

   # MinIO에 업로드 (mc 클라이언트 사용)
   docker exec -it skala-minio-init mc cp /tmp/test.wav myminio/skala/test.wav

   # 브라우저에서 확인
   # http://localhost:9000/skala/test.wav
   ```

### Step 4: FastAPI 설정 수정

`app/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # S3 (MinIO for local, AWS S3 for production)
    S3_ENDPOINT_URL: str = "http://localhost:9000"  # MinIO
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin123"
    S3_BUCKET_NAME: str = "skala"
    S3_REGION: str = "us-east-1"  # MinIO에서는 무시됨

    # Spring 2
    SPRING2_BASE_URL: str = "http://localhost:8082"

    class Config:
        env_file = ".env"

settings = Settings()
```

`.env` 파일:

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO (로컬 개발)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_BUCKET_NAME=skala
S3_REGION=us-east-1

# Spring 2
SPRING2_BASE_URL=http://localhost:8082
```

### Step 5: 종료 및 정리

```bash
# 서비스 종료
docker-compose -f docker-compose.dev.yml down

# 데이터까지 삭제
docker-compose -f docker-compose.dev.yml down -v
```

---

## 🚀 Option 1: 로컬 개발 (최소 설정)

### Redis 설치

#### macOS (Homebrew)
```bash
brew install redis
brew services start redis

# 테스트
redis-cli ping
# 응답: PONG
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 테스트
redis-cli ping
```

#### Windows (WSL 권장)
```bash
# WSL에서 Ubuntu 명령어 동일
```

### MinIO 설치

#### macOS/Linux
```bash
# 다운로드
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio

# 실행
mkdir -p ~/minio-data
./minio server ~/minio-data --console-address ":9001"
```

#### Docker (권장)
```bash
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin123" \
  -v ~/minio-data:/data \
  minio/minio server /data --console-address ":9001"
```

---

## ☁️ Option 2: 클라우드 Free Tier

### Redis Cloud (무료)

1. **회원가입:**
   - https://redis.com/try-free/
   - Free Plan: 30MB (세션 저장 충분)

2. **데이터베이스 생성:**
   - Region: 가까운 리전 선택
   - Cloud: AWS
   - 엔드포인트 메모:
     ```
     redis-12345.c123.us-east-1-2.ec2.cloud.redislabs.com:12345
     ```

3. **설정:**
   ```bash
   # .env
   REDIS_URL=redis://default:password@redis-12345.c123.us-east-1-2.ec2.cloud.redislabs.com:12345
   ```

### AWS S3 Free Tier

1. **AWS 계정 생성:**
   - https://aws.amazon.com/free/
   - Free Tier: 5GB 스토리지 (12개월)

2. **S3 버킷 생성:**
   ```bash
   aws s3 mb s3://skala-dev-audio
   ```

3. **IAM 사용자 생성:**
   - S3 권한만 부여
   - Access Key 생성

4. **설정:**
   ```bash
   # .env
   S3_ENDPOINT_URL=  # 비워두면 기본 AWS S3
   S3_ACCESS_KEY=AKIAXXXXXXX
   S3_SECRET_KEY=xxxxxxxxxxxxxx
   S3_BUCKET_NAME=skala-dev-audio
   S3_REGION=ap-northeast-2
   ```

---

## 🏢 Option 3: AWS 프로덕션

### ElastiCache for Redis

```bash
# AWS CLI로 생성
aws elasticache create-cache-cluster \
  --cache-cluster-id skala-redis \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --num-cache-nodes 1 \
  --region ap-northeast-2
```

### S3 프로덕션 설정

```bash
# 버킷 생성
aws s3 mb s3://skala-prod-audio --region ap-northeast-2

# 수명 주기 정책 (30일 후 Glacier 이동)
cat > lifecycle.json <<EOF
{
  "Rules": [
    {
      "Id": "ArchiveOldAudio",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket skala-prod-audio \
  --lifecycle-configuration file://lifecycle.json
```

---

## 🔧 Spring 2 S3 클라이언트 구성

Spring 2에서 S3 업로드를 처리하므로, Spring 2 설정도 필요합니다.

### build.gradle (Spring 2)

```gradle
dependencies {
    // AWS SDK v2
    implementation 'software.amazon.awssdk:s3:2.20.0'

    // 또는 Spring Cloud AWS
    implementation 'io.awspring.cloud:spring-cloud-aws-starter-s3:3.0.0'
}
```

### application.yml (Spring 2)

```yaml
spring:
  cloud:
    aws:
      region:
        static: ap-northeast-2
      s3:
        endpoint: ${S3_ENDPOINT_URL:}  # MinIO: http://localhost:9000, AWS: 비워두기
        bucket: ${S3_BUCKET_NAME:skala}
      credentials:
        access-key: ${S3_ACCESS_KEY}
        secret-key: ${S3_SECRET_KEY}
```

### S3Service.java (Spring 2)

```java
@Service
@RequiredArgsConstructor
public class S3Service {
    private final S3Client s3Client;

    @Value("${spring.cloud.aws.s3.bucket}")
    private String bucketName;

    public String uploadAudio(byte[] audioData, String sessionId, int utteranceIndex) {
        String key = String.format("sessions/%s/utterance_%d.wav", sessionId, utteranceIndex);

        PutObjectRequest request = PutObjectRequest.builder()
            .bucket(bucketName)
            .key(key)
            .contentType("audio/wav")
            .build();

        s3Client.putObject(request, RequestBody.fromBytes(audioData));

        return String.format("s3://%s/%s", bucketName, key);
    }
}
```

---

## 🧪 테스트 스크립트

### Redis 연결 테스트

```python
# test_redis.py
import asyncio
import redis.asyncio as redis

async def test_redis():
    client = redis.from_url("redis://localhost:6379/0", decode_responses=True)

    # 쓰기
    await client.set("test_key", "hello")

    # 읽기
    value = await client.get("test_key")
    print(f"Value: {value}")

    # 삭제
    await client.delete("test_key")

    await client.close()

asyncio.run(test_redis())
```

### S3 (MinIO) 연결 테스트

```python
# test_s3.py
import boto3
from botocore.client import Config

s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin123',
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

# 업로드
with open('test.wav', 'rb') as f:
    s3_client.put_object(
        Bucket='skala',
        Key='test/test.wav',
        Body=f,
        ContentType='audio/wav'
    )

print("Upload successful!")

# 다운로드
response = s3_client.get_object(Bucket='skala', Key='test/test.wav')
data = response['Body'].read()
print(f"Downloaded {len(data)} bytes")
```

---

## 📊 환경별 설정 요약

### 개발 환경 (.env.dev)

```bash
# Redis - Docker Compose
REDIS_URL=redis://localhost:6379/0

# S3 - MinIO
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_BUCKET_NAME=skala
S3_REGION=us-east-1
```

### 스테이징 환경 (.env.staging)

```bash
# Redis - Redis Cloud
REDIS_URL=redis://default:password@redis-staging.cloud.redislabs.com:12345

# S3 - AWS Free Tier
S3_ENDPOINT_URL=
S3_ACCESS_KEY=AKIAXXXXXXX
S3_SECRET_KEY=xxxxxxxxxxxxxx
S3_BUCKET_NAME=skala-staging-audio
S3_REGION=ap-northeast-2
```

### 프로덕션 환경 (.env.prod)

```bash
# Redis - ElastiCache
REDIS_URL=redis://skala-redis.abc123.ng.0001.apne2.cache.amazonaws.com:6379

# S3 - AWS S3
S3_ENDPOINT_URL=
S3_ACCESS_KEY=AKIAXXXXXXX
S3_SECRET_KEY=xxxxxxxxxxxxxx
S3_BUCKET_NAME=skala-prod-audio
S3_REGION=ap-northeast-2
```

---

## 🔒 보안 고려사항

### Redis 보안

1. **비밀번호 설정 (프로덕션)**
   ```bash
   # redis.conf
   requirepass your-strong-password
   ```

2. **방화벽 설정**
   - 내부 네트워크만 접근 허용

### S3 보안

1. **IAM 최소 권한**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:PutObject",
           "s3:GetObject"
         ],
         "Resource": "arn:aws:s3:::skala-prod-audio/*"
       }
     ]
   }
   ```

2. **버킷 정책**
   - 퍼블릭 접근 차단
   - Spring 2만 접근 가능

---

## 📝 다음 단계

1. **Docker Compose 실행**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **FastAPI 설정 확인**
   ```bash
   # .env 파일 생성
   cp .env.example .env
   ```

3. **테스트 스크립트 실행**
   ```bash
   python test_redis.py
   python test_s3.py
   ```

4. **Spring 2 설정 동기화**
   - Spring 2에도 동일한 S3 설정 적용

5. **WebSocket 서버 시작**
   ```bash
   uvicorn app.main:app --reload
   ```

---

## 🆘 트러블슈팅

### Redis 연결 실패

```bash
# Redis 실행 확인
docker ps | grep redis

# Redis 로그 확인
docker logs skala-redis

# 포트 충돌 확인
lsof -i :6379
```

### MinIO 연결 실패

```bash
# MinIO 실행 확인
docker ps | grep minio

# MinIO 로그 확인
docker logs skala-minio

# 버킷 확인
docker exec -it skala-minio mc ls myminio/
```

### S3 업로드 실패 (Spring 2)

```bash
# Spring 2 로그 확인
tail -f logs/spring2.log | grep S3

# MinIO 액세스 로그
docker logs skala-minio | grep PUT
```

---

**작성자:** Claude Code
**최종 수정:** 2025-11-17
**문서 위치:** `/docs/redis_s3_setup_guide.md`