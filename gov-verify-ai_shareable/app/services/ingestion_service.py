import shutil
import uuid

from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.constants import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES
)
from app.core.exceptions import AppException

from app.core.logger import logger


# =========================================
# INGESTION SERVICE
# =========================================

class IngestionService:


    # =====================================
    # FILE VALIDATION
    # =====================================

    @staticmethod
    async def validate_file(
        file: UploadFile
    ):

        extension = (
            Path(file.filename)
            .suffix
            .lower()
        )

        # ---------------------------------
        # EXTENSION VALIDATION
        # ---------------------------------

        if extension not in ALLOWED_EXTENSIONS:

            raise AppException(
                message=(
                    "Unsupported file extension"
                ),
                error_code=(
                    "INVALID_FILE_EXTENSION"
                ),
                status_code=400
            )
        logger.info(
            "File details",
            filename=file.filename,
            content_type=file.content_type
            )


        if (
            file.content_type
            not in ALLOWED_MIME_TYPES
        ):

            raise AppException(
                message=(
                    "Unsupported MIME type"
                ),
                error_code="INVALID_MIME_TYPE",
                status_code=400
            )

        # ---------------------------------
        # FILE SIZE VALIDATION
        # ---------------------------------

        contents = await file.read()

        file_size = len(contents)

        file_size_mb = (
            file_size / (1024 * 1024)
        )

        if (
            file_size_mb
            > settings.MAX_FILE_SIZE_MB
        ):

            raise AppException(
                message=(
                    "File exceeds allowed size"
                ),
                error_code="FILE_TOO_LARGE",
                status_code=400
            )

        # RESET POINTER
        await file.seek(0)

        return file_size


    # =====================================
    # FILE STORAGE
    # =====================================

    @staticmethod
    async def save_file(
        file: UploadFile
    ):

        extension = (
            Path(file.filename)
            .suffix
            .lower()
        )

        generated_filename = (
            f"{uuid.uuid4()}{extension}"
        )

        save_path = (
            Path(settings.UPLOAD_DIR)
            / generated_filename
        )

        with open(save_path, "wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        return (
            generated_filename,
            str(save_path)
        )


    # =====================================
    # MAIN INGESTION PIPELINE
    # =====================================

    @staticmethod
    async def process_upload(
        file: UploadFile
    ):

        logger.info(
            "Upload processing started",
            filename=file.filename
        )

        file_size = (
            await IngestionService
            .validate_file(file)
        )

        (
            generated_filename,
            file_path
        ) = await IngestionService.save_file(
            file
        )

        logger.info(
            "Upload processing complete",
            stored_filename=generated_filename
        )

        return {
            "request_id": str(uuid.uuid4()),

            "filename": generated_filename,

            "original_filename": (
                file.filename
            ),

            "content_type": (
                file.content_type
            ),

            "file_size": file_size,

            "file_path": file_path,

            "status": "SUCCESS",

            "message": (
                "File uploaded successfully"
            )
        }