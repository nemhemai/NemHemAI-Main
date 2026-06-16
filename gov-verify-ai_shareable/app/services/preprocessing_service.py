import uuid

from pathlib import Path

import cv2
import numpy as np

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logger import logger


# =========================================
# PREPROCESSING SERVICE
# =========================================

class PreprocessingService:


    # =====================================
    # IMAGE PREPROCESSING
    # =====================================

    @staticmethod
    def preprocess_image(
        image_path: str,
        page_number: int
    ):

        image = cv2.imread(image_path)

        if image is None:

            raise AppException(
                message="Unable to read image",
                error_code="INVALID_IMAGE",
                status_code=400
            )

        logger.info(
            "Original image dimensions",
            width=image.shape[1],
            height=image.shape[0]
        )

        # =====================================
        # STEP 1: AUTO-ORIENT (fix upside-down / rotated images)
        # =====================================
        image = PreprocessingService._auto_orient(image)

        # =====================================
        # RESIZE LARGE IMAGES
        # =====================================

        height, width = image.shape[:2]

        max_width = 1000

        if width > max_width:

            scale = max_width / width

            image = cv2.resize(
                image,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_AREA
            )

            logger.info(
                "Image resized",
                new_width=image.shape[1],
                new_height=image.shape[0]
            )

        # =====================================
        # SHARPEN (mild unsharp mask to improve
        # OCR accuracy on real card photos)
        # =====================================

        blurred = cv2.GaussianBlur(image, (0, 0), 3)
        sharpened = cv2.addWeighted(image, 1.5, blurred, -0.5, 0)

        # =====================================
        # SAVE PROCESSED IMAGE
        # =====================================

        filename = (
            f"{uuid.uuid4()}.png"
        )

        save_path = (
            Path(settings.PROCESSED_DIR)
            / filename
        )

        cv2.imwrite(
            str(save_path),
            sharpened
        )

        logger.info(
            "Processed image saved",
            path=str(save_path)
        )

        return {

            "page_number": page_number,

            "processed_path": str(
                save_path
            )
        }

    @staticmethod
    def _auto_orient(image):
        """
        Detect and correct document orientation by trying all four rotations
        and choosing the one with the highest text density (non-white pixel count
        in horizontal text projection). This reliably fixes upside-down and
        90-degree rotated documents without requiring EXIF data.
        """
        def _text_score(img):
            """Count dark pixels in horizontal projection — more = more text rows."""
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            # Sum dark pixels per row
            row_sums = np.sum(binary, axis=1)
            # Text density: number of rows with significant content
            threshold = binary.shape[1] * 0.01  # at least 1% of width
            text_rows = np.sum(row_sums > threshold)
            # Also factor in total dark pixels for robustness
            return int(text_rows * 1000 + np.sum(binary))

        rotations = [
            (0,   image),
            (90,  cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)),
            (180, cv2.rotate(image, cv2.ROTATE_180)),
            (270, cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)),
        ]

        best_angle, best_img, best_score = 0, image, _text_score(image)

        for angle, rotated in rotations[1:]:
            score = _text_score(rotated)
            if score > best_score:
                best_score = score
                best_angle = angle
                best_img = rotated

        if best_angle != 0:
            logger.info(f"Auto-oriented image: rotated {best_angle}° to correct orientation")

        return best_img

    # =====================================
    # MAIN PREPROCESSING PIPELINE
    # =====================================

    @staticmethod
    def preprocess_document(
        normalized_pages: list
    ):

        logger.info(
            "Preprocessing started"
        )

        processed_pages = []

        for page in normalized_pages:

            processed_page = (
                PreprocessingService
                .preprocess_image(
                    image_path=(
                        page[
                            "normalized_path"
                        ]
                    ),
                    page_number=(
                        page[
                            "page_number"
                        ]
                    )
                )
            )

            processed_pages.append(
                processed_page
            )

        logger.info(
            "Preprocessing complete",
            total_pages=len(
                processed_pages
            )
        )

        return {

            "request_id": str(
                uuid.uuid4()
            ),

            "total_pages": len(
                processed_pages
            ),

            "processed_pages": (
                processed_pages
            ),

            "status": "SUCCESS"
        }