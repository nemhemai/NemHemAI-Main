#app/ocr_v2/core/pipeline.py

from app.ocr_v2.cleanup.normalization import canonicalize_unicode
from app.ocr_v2.cleanup.script_cleanup import remove_mixed_script_noise
from app.ocr_v2.cleanup.noise import filter_ocr_noise
from app.ocr_v2.cleanup.repair import repair_indic_confusions


def correct_ocr_text(text: str):

    unicode_cleaned = canonicalize_unicode(
        text
    )

    script_cleaned = remove_mixed_script_noise(
        unicode_cleaned
    )

    noise_filtered = filter_ocr_noise(
        script_cleaned
    )

    final_cleaned = repair_indic_confusions(
        noise_filtered
    )

    return {

        "unicode_cleaned": unicode_cleaned,

        "script_cleaned": script_cleaned,

        "noise_filtered": noise_filtered,

        "final_cleaned": final_cleaned,
    }