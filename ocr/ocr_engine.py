import os
import numpy as np
from paddleocr import PaddleOCR


# ============================================================
# Lazy OCR initialization
# ============================================================

ocr = None


def get_ocr():
    global ocr

    if ocr is None:
        print("Initializing PaddleOCR...")

        ocr = PaddleOCR(
            lang="en",
            enable_mkldnn=False,
            cpu_threads=2,
            rec_batch_num=1,
        )

        print("PaddleOCR initialized successfully.")

    return ocr


# ============================================================
# Parse PaddleOCR 2.x result
# ============================================================

def parse_receipt_boxes(ocr_results, y_tolerance=12, min_score=0.55):
    """
    Convert PaddleOCR 2.x OCR output into readable lines.

    PaddleOCR 2.x output format:

    [
        [
            [
                [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
                ["text", score]
            ],
            ...
        ]
    ]
    """

    if not ocr_results:
        return ""

    if not ocr_results[0]:
        return ""

    parsed_items = []

    try:
        for item in ocr_results[0]:

            if not item or len(item) < 2:
                continue

            box = item[0]
            text_info = item[1]

            if not text_info or len(text_info) < 2:
                continue

            text = str(text_info[0]).strip()
            score = float(text_info[1])

            if not text:
                continue

            if score < min_score:
                continue

            # Get coordinates
            x_min = min(point[0] for point in box)

            y_min = min(point[1] for point in box)

            y_max = max(point[1] for point in box)

            y_center = (y_min + y_max) / 2.0

            parsed_items.append(
                {
                    "text": text,
                    "x": x_min,
                    "y_center": y_center,
                    "score": score,
                }
            )

    except Exception as e:

        print(f"Error while parsing OCR result: {e}")

        return ""

    if not parsed_items:
        return ""

    # --------------------------------------------------------
    # Sort top -> bottom
    # --------------------------------------------------------

    parsed_items.sort(
        key=lambda item: item["y_center"]
    )

    # --------------------------------------------------------
    # Group words into lines
    # --------------------------------------------------------

    lines = []

    current_line = []

    current_y = None

    for item in parsed_items:

        if (
            current_y is None
            or abs(item["y_center"] - current_y)
            <= y_tolerance
        ):

            current_line.append(item)

            current_y = float(
                np.mean(
                    [
                        x["y_center"]
                        for x in current_line
                    ]
                )
            )

        else:

            # Sort current line left -> right
            current_line.sort(
                key=lambda item: item["x"]
            )

            lines.append(
                "   ".join(
                    item["text"]
                    for item in current_line
                )
            )

            current_line = [item]

            current_y = item["y_center"]

    # --------------------------------------------------------
    # Add final line
    # --------------------------------------------------------

    if current_line:

        current_line.sort(
            key=lambda item: item["x"]
        )

        lines.append(
            "   ".join(
                item["text"]
                for item in current_line
            )
        )

    return "\n".join(lines)


# ============================================================
# OCR extraction
# ============================================================

def extract_best_text(images: dict) -> str:
    """
    Run OCR on the available image variants.

    Order:
        1. Original
        2. Gray
        3. Threshold
    """

    preferred_images = [
        images.get("original"),
        images.get("gray"),
        images.get("threshold"),
    ]

    ocr_engine = get_ocr()

    for path in preferred_images:

        if not path:
            continue

        if not os.path.exists(path):
            print(f"OCR image not found: {path}")
            continue

        print(f"Running OCR on: {path}")

        try:

            # PaddleOCR 2.x API
            raw_result = ocr_engine.ocr(
                path,
                cls=False
            )

            print(f"OCR completed: {path}")

            if not raw_result:
                print("OCR returned empty result.")
                continue

            if not raw_result[0]:
                print("OCR returned no text boxes.")
                continue

            text = parse_receipt_boxes(
                raw_result,
                y_tolerance=12,
                min_score=0.55,
            )

            if text.strip():

                print("OCR text extracted successfully.")

                return text

            print("OCR detected boxes but no usable text.")

        except Exception as e:

            print(
                f"OCR failed for {path}: "
                f"{type(e).__name__}: {e}"
            )

            continue

    print("OCR could not extract any text.")

    return ""