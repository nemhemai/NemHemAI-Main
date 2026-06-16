# generate_media_dataset.py

import argparse
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import qrcode
from faker import Faker
from PIL import Image, ImageDraw, ImageFilter, ImageFont

fake = Faker("en_IN")

BASE_DIR = Path("government_test_assets") / "aadhaar"
IMAGE_DIR = BASE_DIR / "images"
PDF_DIR = BASE_DIR / "pdfs"
LABEL_DIR = BASE_DIR / "labels"
FACE_DIR = BASE_DIR / "face_images"
AUGMENT_DIR = BASE_DIR / "augmented"

for path in (IMAGE_DIR, PDF_DIR, LABEL_DIR, FACE_DIR, AUGMENT_DIR):
    path.mkdir(parents=True, exist_ok=True)

FACE_BOX = (640, 120, 900, 320)


def generate_verhoeff_check_digit(number: str) -> str:
    """Compute Verhoeff check digit for a numeric string."""
    d = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
    ]
    p = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    ]
    inv = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]
    c = 0
    for i, digit in enumerate(reversed(number)):
        c = d[c][p[(i + 1) % 8][int(digit)]]
    return str(inv[c])


def generate_aadhaar_number() -> str:
    """Generate a realistic 12-digit Aadhaar-like number."""
    base = "".join(str(random.randint(0, 9)) for _ in range(11))
    check_digit = generate_verhoeff_check_digit(base)
    formatted = f"{base[:4]} {base[4:8]} {base[8:]}{check_digit}"
    return formatted

def generate_pan_number() -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    return (
        random.choice(letters)
        + random.choice(letters)
        + random.choice(letters)
        + random.choice(letters)
        + random.choice(letters)
        + str(random.randint(0, 9))
        + str(random.randint(0, 9))
        + str(random.randint(0, 9))
        + str(random.randint(0, 9))
        + random.choice(letters)
    )


def generate_passport_number() -> str:
    """Generate Passport number."""

    return (
        random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        +
        "".join(random.choice("0123456789") for _ in range(7))
    )

def generate_identity() -> dict:
    """Generate synthetic Aadhaar identity data."""
    gender = random.choice(["MALE", "FEMALE"])
    dob = fake.date_of_birth(minimum_age=18, maximum_age=80).strftime("%d/%m/%Y")
    address = fake.address().replace("\n", ", ").upper()
    aadhaar = generate_aadhaar_number()
    issued_date = fake.date_between(start_date="-5y", end_date="today").strftime("%d/%m/%Y")

    return {
        "document_type": "AADHAAR",
        "name": fake.name().upper(),
        "father_name": f"{fake.first_name().upper()} {fake.last_name().upper()}",
        "dob": dob,
        "gender": gender,
        "address": address,
        "pincode": address.split()[-1] if address.split()[-1].isdigit() else "",
        "aadhaar_number": aadhaar,
        "issued_date": issued_date,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

def generate_pan_identity() -> dict:

    gender = random.choice(["MALE", "FEMALE"])

    return {
        "document_type": "PAN",
        "name": fake.name().upper(),
        "father_name": f"{fake.first_name().upper()} {fake.last_name().upper()}",
        "dob": fake.date_of_birth(minimum_age=18,maximum_age=80).strftime("%d/%m/%Y"),
        "gender": gender,
        "pan_number": generate_pan_number(),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
def generate_passport_identity() -> dict:

    gender = random.choice(["MALE", "FEMALE"])

    return {
        "document_type": "PASSPORT",
        "surname": fake.last_name().upper(),
        "given_name": fake.first_name().upper(),
        "passport_number": generate_passport_number(),
        "gender": gender,
        "dob": fake.date_of_birth(minimum_age=18,maximum_age=80).strftime("%d/%m/%Y"),
        "place_of_birth": fake.city().upper(),
        "place_of_issue": fake.city().upper(),
        "issue_date": fake.date_between(start_date="-10y",end_date="-1y" ).strftime("%d/%m/%Y"),
        "expiry_date": fake.date_between(start_date="+1y",end_date="+10y").strftime("%d/%m/%Y"),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
def generate_qr_code(data: str) -> Image.Image:
    """Create a high-quality QR code for Aadhaar payloads."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=4,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def get_font(size: int):
    """Load a system font or fallback to PIL default."""
    font_candidates = [
        "arial.ttf",
        "Arial.ttf",
        str(Path("C:/Windows/Fonts/arial.ttf")),
        str(Path("C:/Windows/Fonts/Arial.ttf")),
        str(Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")),
        str(Path("/Library/Fonts/Arial.ttf")),
    ]

    for font_path in font_candidates:
        try:
            if Path(font_path).exists():
                return ImageFont.truetype(font_path, size)
            return ImageFont.truetype(font_path, size)
        except IOError:
            continue

    return ImageFont.load_default()


def load_random_face(gender: str) -> Image.Image:

    if gender.upper() == "MALE":
        face_dir = BASE_DIR / "portraits" / "male"
    else:
        face_dir = BASE_DIR / "portraits" / "female"

    face_files = []

    for extension in ["*.jpg", "*.jpeg", "*.png"]:
        face_files.extend(face_dir.glob(extension))

    if not face_files:
        raise RuntimeError(
            f"No portrait images found in {face_dir}"
        )

    selected_face = random.choice(face_files)

    return Image.open(
        selected_face
    ).convert("RGB")


def render_aadhaar_card(identity: dict) -> Image.Image:
    """Render a synthetic Aadhaar card image from identity data."""
    card = Image.new("RGB", (1013, 638), color="#F4F7F6")
    draw = ImageDraw.Draw(card)

    draw.rectangle([20, 20, 993, 618], outline="#9CC9A1", width=3)
    draw.rectangle([32, 32, 981, 110], fill="#0A5C36")
    draw.text((42, 45), "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", fill="white", font=get_font(24))
    draw.text((42, 78), "AADHAAR CARD", fill="white", font=get_font(20))

    field_font = get_font(20)
    label_font = get_font(18)
    small_font = get_font(16)

    draw.text((50, 140), "AADHAAR NUMBER", fill="#1A1A1A", font=label_font)
    draw.text((50, 170), identity["aadhaar_number"], fill="#0F3F35", font=field_font)

    draw.text((50, 230), "NAME", fill="#1A1A1A", font=label_font)
    draw.text((50, 260), identity["name"], fill="#111111", font=field_font)

    draw.text((50, 320), "FATHER'S NAME", fill="#1A1A1A", font=label_font)
    draw.text((50, 350), identity["father_name"], fill="#111111", font=field_font)

    draw.text((50, 410), "DATE OF BIRTH", fill="#1A1A1A", font=label_font)
    draw.text((50, 440), identity["dob"], fill="#111111", font=field_font)

    draw.text((50, 500), "GENDER", fill="#1A1A1A", font=label_font)
    draw.text((180, 500), identity["gender"], fill="#111111", font=field_font)

    address_text = f"ADDRESS: {identity['address']}"
    draw.text((50, 540), address_text[:90], fill="#111111", font=small_font)
    if len(address_text) > 90:
        draw.text((50, 565), address_text[90:180], fill="#111111", font=small_font)

    portrait = load_random_face(identity["gender"])
    portrait = portrait.resize(
        (
            FACE_BOX[2] - FACE_BOX[0],
            FACE_BOX[3] - FACE_BOX[1],
        ),
        Image.LANCZOS,
    )
    card.paste(portrait, (FACE_BOX[0], FACE_BOX[1]))

    draw.rectangle(FACE_BOX, outline="#333333", width=2)

    draw.text((620, 140), f"ISSUED: {identity['issued_date']}", fill="#111111", font=label_font)
    draw.text((620, 170), f"PINCODE: {identity['pincode']}", fill="#111111", font=label_font)

    qr = generate_qr_code(json.dumps({"aadhaar_number": identity["aadhaar_number"], "name": identity["name"]}))
    qr = qr.resize((240, 240), Image.LANCZOS)
    card.paste(qr, (660, 330))

    draw.rectangle([630, 320, 910, 580], outline="#4D7B6A", width=2)
    draw.text((640, 600), "Scan for verification", fill="#333333", font=small_font)

    return card

def render_pan_card(identity: dict) -> Image.Image:
    """Render a realistic synthetic PAN card."""

    card = Image.new("RGB", (1012, 638), color="#BFE8FF")
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([10, 10, 1002, 628],radius=20,outline="#5B8DB8",width=3)
    field_font = get_font(24)
    label_font = get_font(20)
    small_font = get_font(16)
    draw.text((35, 35),"INCOME TAX DEPARTMENT",fill="#2D1E1E",font=get_font(26))
    draw.text((720, 35),"GOVT OF INDIA",fill="#2D1E1E",font=get_font(26))
    draw.text((40, 120),identity["name"],fill="#111111",font=field_font)
    draw.text((40, 190),identity["father_name"],fill="#111111",font=field_font)
    draw.text((40, 260),identity["dob"],fill="#111111",font=field_font)
    draw.text((40, 340),"Permanent Account Number",fill="#1F3A93",font=label_font)
    draw.text((40, 380),identity["pan_number"],fill="#000000",font=get_font(28))
    PAN_FACE_BOX = (720,300,920,560)

    portrait = load_random_face(identity["gender"])

    portrait = portrait.resize((PAN_FACE_BOX[2] - PAN_FACE_BOX[0],PAN_FACE_BOX[3] - PAN_FACE_BOX[1] ),Image.LANCZOS)

    card.paste(portrait,(PAN_FACE_BOX[0],PAN_FACE_BOX[1]))
    draw.rectangle(PAN_FACE_BOX,outline="#333333",width=2)
    draw.text((40, 565),identity["pan_number"],fill="#1F3A93",font=field_font)

    return card

def render_passport_card(identity: dict) -> Image.Image:

    card = Image.new("RGB", (1200, 850), color="#F6F1E7")
    draw = ImageDraw.Draw(card)

    field_font = get_font(22)
    label_font = get_font(18)
    title_font = get_font(30)
    small_font = get_font(14)

    draw.rectangle([20, 20, 1180, 830], outline="#444444", width=2)

    draw.text((430, 35), "REPUBLIC OF INDIA", fill="#222222", font=title_font)
    draw.text((500, 75), "PASSPORT", fill="#222222", font=title_font)

    PASSPORT_FACE_BOX = (50, 140, 250, 380)

    portrait = load_random_face(identity["gender"])

    portrait = portrait.resize(
        (
            PASSPORT_FACE_BOX[2] - PASSPORT_FACE_BOX[0],
            PASSPORT_FACE_BOX[3] - PASSPORT_FACE_BOX[1]
        ),
        Image.LANCZOS
    )

    card.paste(
        portrait,
        (
            PASSPORT_FACE_BOX[0],
            PASSPORT_FACE_BOX[1]
        )
    )

    draw.rectangle(
        PASSPORT_FACE_BOX,
        outline="#333333",
        width=2
    )

    draw.text((320, 140), "Passport No.", fill="black", font=label_font)
    draw.text((550, 140), identity["passport_number"], fill="black", font=field_font)

    draw.text((320, 190), "Surname", fill="black", font=label_font)
    draw.text((550, 190), identity["surname"], fill="black", font=field_font)

    draw.text((320, 240), "Given Name", fill="black", font=label_font)
    draw.text((550, 240), identity["given_name"], fill="black", font=field_font)

    draw.text((320, 290), "Nationality", fill="black", font=label_font)
    draw.text((550, 290), "INDIAN", fill="black", font=field_font)

    draw.text((320, 340), "Sex", fill="black", font=label_font)
    draw.text((550, 340), identity["gender"][0], fill="black", font=field_font)

    draw.text((320, 390), "Date of Birth", fill="black", font=label_font)
    draw.text((550, 390), identity["dob"], fill="black", font=field_font)

    draw.text((320, 440), "Place of Birth", fill="black", font=label_font)
    draw.text((550, 440), identity["place_of_birth"], fill="black", font=field_font)

    draw.text((320, 490), "Place of Issue", fill="black", font=label_font)
    draw.text((550, 490), identity["place_of_issue"], fill="black", font=field_font)

    draw.text((320, 540), "Date of Issue", fill="black", font=label_font)
    draw.text((550, 540), identity["issue_date"], fill="black", font=field_font)

    draw.text((320, 590), "Date of Expiry", fill="black", font=label_font)
    draw.text((550, 590), identity["expiry_date"], fill="black", font=field_font)

    draw.line([60, 430, 250, 430], fill="#000000", width=2)

    draw.text(
        (70, 440),
        identity["surname"],
        fill="#000000",
        font=small_font
    )

    draw.rectangle(
        [30, 720, 1170, 810],
        fill="#EFEFEF"
    )

    mrz1 = f"P<IND{identity['surname']}<<{identity['given_name']}"
    mrz2 = f"{identity['passport_number']}<IND"

    draw.text((40, 735), mrz1.upper(), fill="black", font=field_font)
    draw.text((40, 775), mrz2.upper(), fill="black", font=field_font)

    return card
def save_image_and_pdf(image: Image.Image, image_path: Path, pdf_path: Path) -> None:
    """Save the rendered Aadhaar card as PNG and PDF."""
    image.save(image_path, format="PNG")
    image.save(pdf_path, format="PDF", resolution=100.0)


def extract_face_crop(card: Image.Image) -> Image.Image:
    """Crop the face photo region from the rendered Aadhaar card."""
    return card.crop(FACE_BOX)


def load_image_cv2(path: Path) -> np.ndarray:
    """Load an image from disk as a BGR cv2 array."""
    return cv2.imread(str(path))


def save_cv2_image(path: Path, image: np.ndarray) -> None:
    """Save a cv2 image to disk as PNG."""
    cv2.imwrite(str(path), image)


def apply_blur(image: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(image, (15, 15), 0)


def apply_rotation(image: np.ndarray, angle: float = None) -> np.ndarray:
    if angle is None:
        angle = random.uniform(-12.0, 12.0)
    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(245, 247, 246))


def apply_low_light(image: np.ndarray) -> np.ndarray:
    gamma = random.uniform(1.4, 2.2)
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(image, table)


def apply_over_exposed(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    v = np.clip(v + random.randint(40, 80), 0, 255).astype("uint8")
    return cv2.cvtColor(cv2.merge([h, s, v]), cv2.COLOR_HSV2BGR)

def apply_overexposed_flash( image: np.ndarray) -> np.ndarray:
    bright = apply_over_exposed(image)
    return apply_flash_hotspot(bright)

def apply_flash_hotspot(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    center = (random.randint(w // 4, 3 * w // 4),random.randint(h // 4, 3 * h // 4),)
    radius = random.randint(min(h, w) // 8,min(h, w) // 3)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask,center,radius,255,1)
    mask = cv2.GaussianBlur(mask,(151, 151),0)
    mask = mask.astype(np.float32) / 255.0
    bright = cv2.convertScaleAbs(image,alpha=1.8,beta=120)
    result = image.astype(np.float32)
    for c in range(3):
        result[:, :, c] = (
            result[:, :, c] * (1 - mask)
            + bright[:, :, c] * mask
        )

    return np.clip(
        result,
        0,
        255
    ).astype(np.uint8)

def apply_under_exposed(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    v = np.clip(v - random.randint(40, 80), 0, 255).astype("uint8")
    return cv2.cvtColor(cv2.merge([h, s, v]), cv2.COLOR_HSV2BGR)

def apply_underexposed_flash(image: np.ndarray) -> np.ndarray:
    dark = apply_under_exposed(image)
    return apply_flash_hotspot(dark)

def apply_mobile_photo_style(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    margin = int(min(h, w) * 0.05)
    src = np.float32([[margin, margin], [w - margin, margin], [w - margin, h - margin], [margin, h - margin]])
    dst = src + np.float32(
        [
            [random.uniform(-20, 20), random.uniform(-20, 20)],
            [random.uniform(-20, 20), random.uniform(-20, 20)],
            [random.uniform(-20, 20), random.uniform(-20, 20)],
            [random.uniform(-20, 20), random.uniform(-20, 20)],
        ]
    )
    persp = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(image, persp, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(245, 247, 246))
    noise = np.random.normal(0, 10, warped.shape).astype(np.int16)
    warped = warped.astype(np.int16)
    noisy = np.clip(warped + noise, 0, 255).astype(np.uint8)
    return cv2.addWeighted(noisy, 0.85, np.full_like(noisy, 255), 0.15, 0)


def apply_crop(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    scale = random.uniform(0.72, 0.88)
    new_h, new_w = int(h * scale), int(w * scale)
    y = random.randint(0, h - new_h)
    x = random.randint(0, w - new_w)
    cropped = image[y : y + new_h, x : x + new_w]
    top = (h - new_h) // 2
    left = (w - new_w) // 2
    padded = cv2.copyMakeBorder(cropped, top, h - new_h - top, left, w - new_w - left, cv2.BORDER_CONSTANT, value=(245, 247, 246))
    return padded


def apply_compression(image: np.ndarray) -> np.ndarray:
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), random.randint(20, 45)]
    _, buffer = cv2.imencode(".jpg", image, encode_param)
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)


AUGMENTATIONS = {
    "blurred": apply_blur,
    "rotated": apply_rotation,
    "low_light": apply_low_light,
    "over_exposed": apply_over_exposed,
    "under_exposed": apply_under_exposed,
    "flash_hotspot": apply_flash_hotspot,
    "underexposed_flash": apply_underexposed_flash,
    "overexposed_flash": apply_overexposed_flash,
    "mobile_photo": apply_mobile_photo_style,
    "cropped": apply_crop,
    "compressed": apply_compression,
}

def augment_and_save(image_path: Path, base_name: str) -> list[dict]:
    """Create augmented variants for a generated Aadhaar card."""
    original = load_image_cv2(image_path)
    variants = []

    for variant_name, function in AUGMENTATIONS.items():
        augmented = function(original.copy())
        variant_path = AUGMENT_DIR / f"{base_name}_{variant_name}.png"
        save_cv2_image(variant_path, augmented)
        variants.append({"variant": variant_name, "path": str(variant_path)})

    return variants


def write_label_file(identity: dict, image_path: Path, pdf_path: Path, face_path: Path, variants: list[dict]) -> None:
    """Save ground truth JSON with exact generated values and file references."""
    label = {
        "id": image_path.stem,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "identity": identity,
        "files": {
            "image": str(image_path),
            "pdf": str(pdf_path),
            "face_image": str(face_path),
            "augmented_variants": variants,
        },
    }
    label_path = LABEL_DIR / f"{image_path.stem}.json"
    label_path.write_text(json.dumps(label, indent=2), encoding="utf-8")


def build_aadhaar_sample(index: int) -> None:
    """Generate one synthetic Aadhaar sample with image, PDF, face crop, augmentation, and labels."""
    identity = generate_identity()
    image_path = IMAGE_DIR / f"aadhaar_{index:04d}.png"
    pdf_path = PDF_DIR / f"aadhaar_{index:04d}.pdf"
    face_path = FACE_DIR / f"aadhaar_{index:04d}_face.png"

    rendered = render_aadhaar_card(identity)
    save_image_and_pdf(rendered, image_path, pdf_path)

    face_crop = extract_face_crop(rendered)
    face_crop.save(face_path, format="PNG")

    variants = augment_and_save(image_path, f"aadhaar_{index:04d}")
    write_label_file(identity, image_path, pdf_path, face_path, variants)

def build_pan_sample(index: int) -> None:
    """Generate one synthetic PAN sample."""

    identity = generate_pan_identity()

    image_path = (Path("government_test_assets")/ "pan"/ "images"/ f"pan_{index:04d}.png")
    pdf_path = ( Path("government_test_assets")/ "pan"/ "pdfs"/ f"pan_{index:04d}.pdf")
    face_path = (Path("government_test_assets")/ "pan"/ "face_images"/ f"pan_{index:04d}_face.png")
    rendered = render_pan_card(identity)
    save_image_and_pdf(rendered,image_path,pdf_path)
    face_crop = extract_face_crop(rendered)
    face_crop.save(face_path,format="PNG")
    variants = augment_and_save(image_path,f"pan_{index:04d}")
    write_label_file(identity,image_path,pdf_path,face_path,variants)

def build_passport_sample(index: int) -> None:
    """Generate one synthetic Passport sample."""
    identity = generate_passport_identity()
    image_path = ( Path("government_test_assets")/ "passport"/ "images"/ f"passport_{index:04d}.png")
    pdf_path = (Path("government_test_assets")/ "passport"/ "pdfs"/ f"passport_{index:04d}.pdf")
    face_path = (Path("government_test_assets")/ "passport"/ "face_images"/ f"passport_{index:04d}_face.png")
    rendered = render_passport_card(identity)
    save_image_and_pdf(rendered,image_path,pdf_path)
    face_crop = extract_face_crop(rendered)
    face_crop.save(face_path,format="PNG")
    variants = augment_and_save(image_path,f"passport_{index:04d}")
    write_label_file(identity,image_path,pdf_path,face_path,variants)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a synthetic Aadhaar dataset with augmented media and ground truth labels.")
    parser.add_argument("--count", type=int, default=100, help="Number of Aadhaar samples to generate")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(f"Generating {args.count} synthetic samples...")

    for index in range(args.count):
        build_aadhaar_sample(index)
        build_pan_sample(index)
        build_passport_sample(index)
    
    print("Completed Aadhaar, PAN and Passport dataset generation.")
    print(f"Images: {len(list(IMAGE_DIR.glob('*.png')))}")
    print(f"Face crops: {len(list(FACE_DIR.glob('*.png')))}")
    print(f"PDFs: {len(list(PDF_DIR.glob('*.pdf')))}")
    print(f"Labels: {len(list(LABEL_DIR.glob('*.json')))}")
    print(f"Augmented variants: {len(list(AUGMENT_DIR.glob('*.png')))}")