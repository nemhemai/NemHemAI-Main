# Government Document Verification Agent

This repository contains an automated government document verification agent that processes **Aadhaar Cards**, **PAN Cards**, and **Passports**. It pipelines page layout normalization, OpenCV contrast enhancement, PaddleOCR text extraction, keyword classification, regex parsing, validation check-sums, database lookup cross-validation, image fraud detection, and a final decision aggregator.

It also features a premium glassmorphic dashboard for interactive, visual document uploads and real-time step-by-step pipeline updates.

---

## 📋 Pipeline Architecture

The platform runs the uploaded document through the following 10 steps:
1. **Document Upload**: Receives files via PDF or image (`PNG`/`JPEG`).
2. **Layout Normalization**: Converts PDFs or non-standard layouts into a standard page-by-page PNG representation.
3. **Preprocessing**: Grayscales, contrast boosts (using CLAHE), and applies Otsu thresholding to optimize OCR readability.
4. **OCR Extraction**: Extracts raw text blocks using PaddleOCR (running on optimized preprocessed images for maximum speed and accuracy).
5. **Document Classification**: Evaluates OCR keywords to identify document type (`AADHAAR`, `PAN`, `PASSPORT`, or `UNKNOWN`).
6. **Field Parser**: Runs specialized regex extractors for each document type to obtain visual fields (Names, Dates, Numbers, MRZ).
7. **Verification Rules**: Applies format validation and checksum rules (e.g. Aadhaar Verhoeff algorithm, PAN entity checksums, and date range checks).
8. **Cross-Validation**: 
   - Checks visual fields against parsed MRZ fields (for passports).
   - Reference checks visual fields (Name, DOB, Document Number) against a mock registry loaded from synthetic asset data.
9. **Fraud Detection**: Analyzes image metrics using OpenCV to detect blur, hot-spot camera flash glares, over-exposure, cropping, and face presence.
10. **Decision Aggregation**: Blends check results and fraud risk scores to produce a final verdict (`APPROVED`, `REJECTED`, or `MANUAL_REVIEW`) with clear reasons.

---

## 📁 Repository Structure (What to Zip & Send)

When sending this project to your colleague, package the following files and directories:

```text
gov-verify-ai/
├── app/                        # FastAPI Application Core
│   ├── api/                    # Endpoint routes and controllers
│   ├── core/                   # Config, logging, and constants
│   ├── schemas/                # Pydantic request & response models
│   ├── services/               # Modular business logic services (OCR, Classifier, Fraud, etc.)
│   └── templates/              # HTML frontend template (index.html dashboard)
├── requirements/               # Package dependencies configuration
│   ├── base.txt                # Core packages
│   ├── dev.txt                 # Development testing utilities
│   └── prod.txt                # Production packages
├── .env                        # Server configurations (port, directories)
├── README.md                   # This documentation guide
├── run.py                      # Main entrypoint script to run the server
├── test_services.py            # Local in-process verification pipeline test script
└── test_pipeline_api.py        # HTTP API endpoint verification test script
```

> [!WARNING]
> **DO NOT SEND** the virtual environment folder (`venv/`), python compilation cache folders (`__pycache__/`), or the local database storage directories (`storage/` which contains uploads, temp files, and logs). These are machine-specific and will bloat the size of the ZIP file.

---

## 🚀 Setup & Execution Instructions

Follow these steps to set up and run the document verification agent on your local machine:

### 1. Prerequisite Installations
- Ensure you have **Python 3.10** or **Python 3.11** installed.
- Ensure **Poppler** and **Tesseract** are installed and added to your system `PATH` (required for PDF layout normalization and image extraction).

### 2. Set Up a Virtual Environment
Navigate to the root folder in your terminal and create a new virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows Powershell)
.\venv\Scripts\Activate.ps1

# Activate virtual environment (macOS/Linux)
source venv/bin/activate
```

### 3. Install Dependencies
Install all package requirements defined in the repository:
```bash
pip install -r requirements/base.txt
```

### 4. Run the FastAPI Server
Start the development server using the main entry script:
```bash
python run.py
```
The server will start at: **`http://localhost:8000/`** (redirects to `/api/v1/` automatically).

### 5. Open the Interactive Visual UI
Open your web browser and navigate to:
**[http://localhost:8000/](http://localhost:8000/)**

You can drag and drop or upload any ID document (Aadhaar, PAN, or Passport) to visualize the automated verification process step-by-step.

---

## 🧪 Testing the Codebase

You can run automated verification runs using the built-in test scripts:

- **Local Pipeline Test**: Run `python test_services.py` to process Aadhaar, PAN, and Passport images end-to-end and see console printouts without the FastAPI server overhead.
- **API Endpoint Test**: With the server running, execute `python test_pipeline_api.py` to trigger a synthetic upload request and verify endpoint response payloads.
