import os
import cv2
import numpy as np
from paddleocr import PaddleOCR

# Global OCR instance to avoid reloading weights on every API request
ocr = PaddleOCR(
    lang="en", use_angle_cls=True, use_space_char=True
)


def parse_receipt_boxes(ocr_results, y_tolerance=12, min_score=0.55):
    """Sorts OCR bounding boxes top-to-bottom using y_center
    and left-to-right using x_min.
    """
    if not ocr_results or not ocr_results[0]:
        return ""

    boxes = ocr_results[0]
    parsed_items = []

    for box, (text, score) in boxes:
        if score < min_score:
            continue
        x_min = min(pt[0] for pt in box)
        y_min = min(pt[1] for pt in box)
        y_max = max(pt[1] for pt in box)
        y_center = (y_min + y_max) / 2.0

        parsed_items.append(
            {"text": text, "x": x_min, "y_center": y_center, "score": score}
        )

    parsed_items.sort(key=lambda item: item["y_center"])

    lines = []
    current_line = []
    current_y = None

    for item in parsed_items:
        if current_y is None or abs(item["y_center"] - current_y) <= y_tolerance:
            current_line.append(item)
            current_y = float(np.mean([it["y_center"] for it in current_line]))
        else:
            current_line.sort(key=lambda it: it["x"])
            lines.append("   ".join(it["text"] for it in current_line))

            current_line = [item]
            current_y = item["y_center"]

    if current_line:
        current_line.sort(key=lambda it: it["x"])
        lines.append("   ".join(it["text"] for it in current_line))

    return "\n".join(lines)


def extract_best_text(images: dict) -> str:
    """Run OCR once on the preferred variant, with fallbacks when needed."""
    preferred_images = [
        images.get("threshold"),
        images.get("gray"),
        images.get("original"),
    ]

    for path in preferred_images:
        if not path:
            continue
        if not os.path.exists(path):
            continue

        raw_result = ocr.ocr(path, cls=True)

        if not raw_result or not raw_result[0]:
            continue

        text = parse_receipt_boxes(raw_result)
        if text.strip():
            return text

    return ""