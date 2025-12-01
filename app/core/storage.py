"""
📄 파일명: storage.py
📌 역할: S3 등 외부 스토리지 업로드/다운로드 래퍼.

기능:
    - 음성 파일 업로드 (MP3, WAV)
    - 파일 다운로드
    - Pre-signed URL 생성
    - 파일 삭제
"""

import logging
from datetime import datetime
from typing import Optional
from io import BytesIO

import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class S3StorageService:
    """S3 스토리지 서비스"""

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    def _ensure_bucket_exists(self) -> None:
        """버킷이 존재하는지 확인하고 없으면 생성"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                logger.info(f"Creating bucket: {self.bucket_name}")
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                raise

    def upload_audio(
        self,
        audio_data: bytes,
        session_id: str,
        turn_index: int,
        file_format: str = "mp3"
    ) -> str:
        """
        음성 파일을 S3에 업로드

        Args:
            audio_data: 음성 데이터 바이트
            session_id: 세션 ID
            turn_index: 턴 인덱스
            file_format: 파일 형식 (mp3, wav)

        Returns:
            str: S3 객체 URL
        """
        self._ensure_bucket_exists()

        # 파일 경로 생성: audio/{session_id}/{turn_index}_{timestamp}.{format}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_key = f"audio/{session_id}/{turn_index}_{timestamp}.{file_format}"

        # Content-Type 설정
        content_type = "audio/mpeg" if file_format == "mp3" else "audio/wav"

        try:
            self.s3_client.upload_fileobj(
                BytesIO(audio_data),
                self.bucket_name,
                object_key,
                ExtraArgs={"ContentType": content_type}
            )

            # URL 생성
            url = f"{settings.S3_ENDPOINT_URL}/{self.bucket_name}/{object_key}"
            logger.info(f"Audio uploaded: {url}")
            return url

        except ClientError as e:
            logger.error(f"Failed to upload audio: {e}")
            raise

    def upload_file(
        self,
        file_path: str,
        object_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        로컬 파일을 S3에 업로드

        Args:
            file_path: 로컬 파일 경로
            object_key: S3 객체 키
            content_type: Content-Type 헤더

        Returns:
            str: S3 객체 URL
        """
        self._ensure_bucket_exists()

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args if extra_args else None
            )

            url = f"{settings.S3_ENDPOINT_URL}/{self.bucket_name}/{object_key}"
            logger.info(f"File uploaded: {url}")
            return url

        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            raise

    def download_file(self, object_key: str) -> bytes:
        """
        S3에서 파일 다운로드

        Args:
            object_key: S3 객체 키

        Returns:
            bytes: 파일 데이터
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return response["Body"].read()

        except ClientError as e:
            logger.error(f"Failed to download file: {e}")
            raise

    def get_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600
    ) -> str:
        """
        Pre-signed URL 생성 (임시 접근 URL)

        Args:
            object_key: S3 객체 키
            expiration: URL 만료 시간 (초)

        Returns:
            str: Pre-signed URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": object_key
                },
                ExpiresIn=expiration
            )
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def delete_file(self, object_key: str) -> bool:
        """
        S3에서 파일 삭제

        Args:
            object_key: S3 객체 키

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            logger.info(f"File deleted: {object_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file: {e}")
            return False

    def list_session_audio(self, session_id: str) -> list[dict]:
        """
        세션의 모든 음성 파일 목록 조회

        Args:
            session_id: 세션 ID

        Returns:
            list[dict]: 파일 정보 목록
        """
        prefix = f"audio/{session_id}/"

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            files = []
            for obj in response.get("Contents", []):
                files.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                    "url": f"{settings.S3_ENDPOINT_URL}/{self.bucket_name}/{obj['Key']}"
                })

            return files

        except ClientError as e:
            logger.error(f"Failed to list files: {e}")
            return []


# 싱글톤 인스턴스
_s3_storage_service: Optional[S3StorageService] = None


def get_s3_storage_service() -> S3StorageService:
    """S3 Storage Service 인스턴스 반환"""
    global _s3_storage_service
    if _s3_storage_service is None:
        _s3_storage_service = S3StorageService()
    return _s3_storage_service
