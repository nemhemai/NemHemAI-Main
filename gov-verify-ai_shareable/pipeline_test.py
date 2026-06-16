import os
import mimetypes
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

DATASET_DIR = Path("dataset")


def upload_document(file_path):

    mime_type, _ = mimetypes.guess_type(
        str(file_path)
    )

    with open(file_path, "rb") as f:

        files = {
            "file": (
                os.path.basename(file_path),
                f,
                mime_type
            )
        }

        response = requests.post(
            f"{BASE_URL}/upload",
            files=files
        )

    response.raise_for_status()

    return response.json()


def normalize_document(file_path):

    response = requests.post(
        f"{BASE_URL}/normalize",
        params={
            "file_path": file_path
        }
    )

    response.raise_for_status()

    return response.json()


def preprocess_document(normalized_pages):

    response = requests.post(
        f"{BASE_URL}/preprocess",
        json={
            "normalized_pages": normalized_pages
        }
    )

    response.raise_for_status()

    return response.json()


def perform_ocr(processed_pages):

    response = requests.post(
        f"{BASE_URL}/ocr",
        json={
            "processed_pages": processed_pages
        }
    )

    response.raise_for_status()

    return response.json()


def process_document(file_path):

    print(f"\nProcessing: {file_path}")

    upload_result = upload_document(file_path)

    normalize_result = normalize_document(
        upload_result["file_path"]
    )

    preprocess_result = preprocess_document(
        normalize_result["normalized_pages"]
    )

    ocr_result = perform_ocr(
        preprocess_result["processed_pages"]
    )

    print("\nOCR TEXT:")
    print("-" * 50)
    print(
        ocr_result["extracted_text"][:1000]
    )
    print("-" * 50)

    return ocr_result


def main():

    supported_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".pdf"
    }

    for root, dirs, files in os.walk(DATASET_DIR):

        for file in files:

            path = Path(root) / file

            if path.suffix.lower() not in supported_extensions:
                continue

            try:

                process_document(path)

            except Exception as e:


                print(e)


if __name__ == "__main__":
    main()