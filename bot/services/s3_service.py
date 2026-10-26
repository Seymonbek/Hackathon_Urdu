import os
import logging
from typing import Optional
from bot.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    @staticmethod
    async def upload_document(file_bytes: bytes, filename: str, content_type: str = "application/pdf") -> str:
        """
        AWS S3 ga hujjat yuklaydi.
        Agar AWS kalitlari bo'lmasa, mahalliy 'uploads/' papkasiga saqlaydi.
        """
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            try:
                import boto3
                s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION,
                )
                key = f"documents/{filename}"
                s3_client.put_object(
                    Bucket=settings.AWS_S3_BUCKET,
                    Key=key,
                    Body=file_bytes,
                    ContentType=content_type,
                )
                url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
                logger.info(f"Fayl AWS S3 ga muvaffaqiyatli yuklandi: {url}")
                return url
            except Exception as e:
                logger.warning(f"AWS S3 ga yuklashda xato: {e}. Mahalliy xotiraga saqlanadi.")

        # Mahalliy zaxira (Local storage fallback)
        os.makedirs("uploads", exist_ok=True)
        local_path = os.path.join("uploads", filename)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        return f"/uploads/{filename}"
