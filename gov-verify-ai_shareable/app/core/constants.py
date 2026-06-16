# =========================================
# SUPPORTED FILE EXTENSIONS
# =========================================

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".pdf"
}

# =========================================
# SUPPORTED MIME TYPES
# =========================================

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf"
}

# =========================================
# DOCUMENT TYPES
# =========================================

DOCUMENT_TYPES = {
    "AADHAAR",
    "PAN",
    "PASSPORT",
    "DRIVING_LICENSE",
    "UNKNOWN"
}

# =========================================
# DOCUMENT TYPE CONSTANTS
# =========================================

DOCUMENT_TYPE_AADHAAR = "AADHAAR"

DOCUMENT_TYPE_PAN = "PAN"

DOCUMENT_TYPE_PASSPORT = "PASSPORT"

DOCUMENT_TYPE_DRIVING_LICENSE = "DRIVING_LICENSE"

DOCUMENT_TYPE_UNKNOWN = "UNKNOWN"