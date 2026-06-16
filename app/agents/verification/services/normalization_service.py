import uuid

from pathlib import Path

import fitz

from PIL import Image

from app.agents.verification.core.config import settings
from app.agents.verification.core.exceptions import AppException
from app.agents.verification.core.logger import logger


# =========================================
# NORMALIZATION SERVICE
# =========================================

class NormalizationService:


    # =====================================
    # PDF NORMALIZATION
    # =====================================

    @staticmethod
    def normalize_pdf(
        pdf_path: str
    ):

        normalized_pages = []

        try:

            document = fitz.open(pdf_path)

        except Exception:

            raise AppException(
                message="Invalid PDF document",
                error_code="INVALID_PDF",
                status_code=400
            )

        for page_index in range(len(document)):

            page = document.load_page(
                page_index
            )

            pix = page.get_pixmap(
                dpi=300
            )

            image = Image.frombytes(
                "RGB",
                [pix.width, pix.height],
                pix.samples
            )

            filename = (
                f"{uuid.uuid4()}.png"
            )

            save_path = (
                Path(settings.NORMALIZED_DIR)
                / filename
            )

            image.save(save_path)

            normalized_pages.append({

                "page_number": (
                    page_index + 1
                ),

                "normalized_path": (
                    str(save_path)
                )
            })

        return normalized_pages


    # =====================================
    # IMAGE NORMALIZATION
    # =====================================

    @staticmethod
    def normalize_image(
        image_path: str
    ):

        try:

            image = Image.open(
                image_path
            )

        except Exception:

            raise AppException(
                message="Invalid image file",
                error_code="INVALID_IMAGE",
                status_code=400
            )

        image = image.convert("RGB")

        filename = (
            f"{uuid.uuid4()}.png"
        )

        save_path = (
            Path(settings.NORMALIZED_DIR)
            / filename
        )

        image.save(save_path)

        return [{
            "page_number": 1,
            "normalized_path": str(save_path)
        }]


    # =====================================
    # MAIN NORMALIZATION PIPELINE
    # =====================================

    @staticmethod
    def normalize_document(
        file_path: str
    ):

        logger.info(
            "Normalization started",
            file_path=file_path
        )

        extension = (
            Path(file_path)
            .suffix
            .lower()
        )

        if extension == ".pdf":

            normalized_pages = (
                NormalizationService
                .normalize_pdf(file_path)
            )

            document_type = "PDF"

        else:

            normalized_pages = (
                NormalizationService
                .normalize_image(file_path)
            )

            document_type = "IMAGE"

        logger.info(
            "Normalization complete",
            total_pages=len(
                normalized_pages
            )
        )

        return {

            "request_id": str(
                uuid.uuid4()
            ),

            "document_type": (
                document_type
            ),

            "total_pages": len(
                normalized_pages
            ),

            "normalized_pages": (
                normalized_pages
            ),

            "status": "SUCCESS"
        }