# import os
# import cv2
# import numpy as np
# from paddleocr import PaddleOCR

# # Initialize lazily so the app does not spend a long time loading OCR models
# # during cold starts on hosted platforms such as Render.
# ocr = None


# def get_ocr():
#     global ocr
#     if ocr is None:
#         ocr = PaddleOCR(lang="en", enable_mkldnn=False)
#     return ocr


# def parse_receipt_boxes(ocr_results, y_tolerance=12, min_score=0.55):
#     """Sorts OCR bounding boxes top-to-bottom using y_center
#     and left-to-right using x_min.
#     """
#     if not ocr_results or not ocr_results[0]:
#         return ""

#     first_result = ocr_results[0]
#     if isinstance(first_result, dict):
#         boxes = zip(
#             first_result.get("rec_polys", []),
#             zip(
#                 first_result.get("rec_texts", []),
#                 first_result.get("rec_scores", []),
#             ),
#         )
#     else:
#         boxes = first_result

#     parsed_items = []

#     for box, (text, score) in boxes:
#         if score < min_score:
#             continue
#         x_min = min(pt[0] for pt in box)
#         y_min = min(pt[1] for pt in box)
#         y_max = max(pt[1] for pt in box)
#         y_center = (y_min + y_max) / 2.0

#         parsed_items.append(
#             {"text": text, "x": x_min, "y_center": y_center, "score": score}
#         )

#     parsed_items.sort(key=lambda item: item["y_center"])

#     lines = []
#     current_line = []
#     current_y = None

#     for item in parsed_items:
#         if current_y is None or abs(item["y_center"] - current_y) <= y_tolerance:
#             current_line.append(item)
#             current_y = float(np.mean([it["y_center"] for it in current_line]))
#         else:
#             current_line.sort(key=lambda it: it["x"])
#             lines.append("   ".join(it["text"] for it in current_line))

#             current_line = [item]
#             current_y = item["y_center"]

#     if current_line:
#         current_line.sort(key=lambda it: it["x"])
#         lines.append("   ".join(it["text"] for it in current_line))

#     return "\n".join(lines)


# def extract_best_text(images: dict) -> str:
#     """Run OCR once on the preferred variant, with fallbacks when needed."""
#     preferred_images = [
#         images.get("threshold"),
#         images.get("gray"),
#         images.get("original"),
#     ]

#     ocr_engine = get_ocr()

#     for path in preferred_images:
#         if not path:
#             continue
#         if not os.path.exists(path):
#             continue

#         if hasattr(ocr_engine, "predict"):
#             raw_result = ocr_engine.predict(path)
#         else:
#             try:
#                 raw_result = ocr_engine.ocr(path, cls=True)
#             except TypeError:
#                 raw_result = ocr_engine.ocr(path)

#         if not raw_result or not raw_result[0]:
#             continue

#         text = parse_receipt_boxes(raw_result)
#         if text.strip():
#             return text

#     return ""




















# import os
# import cv2
# import numpy as np
# from paddleocr import PaddleOCR


# # ============================================================
# # Global OCR instance
# # ============================================================

# ocr = None


# # ============================================================
# # Initialize OCR lazily
# # ============================================================

# def get_ocr():
#     global ocr

#     if ocr is None:

#         print("Initializing PaddleOCR...")

#         ocr = PaddleOCR(
#             lang="en",
#             enable_mkldnn=False,
#             cpu_threads=1,
#             rec_batch_num=1,
#             det_limit_side_len=960,
#             det_limit_type="max",
#         )

#         print("PaddleOCR initialized successfully.")

#     return ocr


# # ============================================================
# # Resize image before OCR
# # ============================================================

# def prepare_image(path, max_width=1600, max_height=2200):

#     print(f"Preparing image: {path}")

#     image = cv2.imread(path)

#     if image is None:
#         raise ValueError(f"Could not read image: {path}")

#     height, width = image.shape[:2]

#     print(
#         f"Original image size: "
#         f"{width}x{height}"
#     )

#     # No resize if image is already small
#     if width <= max_width and height <= max_height:

#         print("Image resize not required.")

#         return path

#     scale = min(
#         max_width / width,
#         max_height / height,
#     )

#     new_width = int(width * scale)
#     new_height = int(height * scale)

#     resized = cv2.resize(
#         image,
#         (new_width, new_height),
#         interpolation=cv2.INTER_AREA,
#     )

#     directory = os.path.dirname(path)

#     filename = os.path.basename(path)

#     name, ext = os.path.splitext(filename)

#     resized_path = os.path.join(
#         directory,
#         f"{name}_ocr{ext}"
#     )

#     cv2.imwrite(
#         resized_path,
#         resized,
#     )

#     print(
#         f"Resized image: "
#         f"{new_width}x{new_height}"
#     )

#     print(
#         f"OCR image: {resized_path}"
#     )

#     return resized_path


# # ============================================================
# # Parse OCR result
# # ============================================================

# def parse_receipt_boxes(
#     ocr_results,
#     y_tolerance=12,
#     min_score=0.55,
# ):

#     if not ocr_results:
#         print("OCR result is empty.")

#         return ""

#     parsed_items = []

#     try:

#         first_result = ocr_results[0]
#         if isinstance(first_result, dict):
#             boxes = zip(
#                 first_result.get("rec_polys", first_result.get("dt_polys", [])),
#                 zip(
#                     first_result.get("rec_texts", []),
#                     first_result.get("rec_scores", []),
#                 ),
#             )
#         else:
#             boxes = first_result or []

#         for item in boxes:

#             if not item:
#                 continue

#             if len(item) < 2:
#                 continue

#             box = item[0]

#             text_info = item[1]

#             if not text_info:
#                 continue

#             if len(text_info) < 2:
#                 continue

#             text = str(
#                 text_info[0]
#             ).strip()

#             score = float(
#                 text_info[1]
#             )

#             if not text:
#                 continue

#             if score < min_score:
#                 continue

#             x_min = min(
#                 point[0]
#                 for point in box
#             )

#             y_min = min(
#                 point[1]
#                 for point in box
#             )

#             y_max = max(
#                 point[1]
#                 for point in box
#             )

#             y_center = (
#                 y_min + y_max
#             ) / 2.0

#             parsed_items.append(
#                 {
#                     "text": text,
#                     "x": x_min,
#                     "y_center": y_center,
#                     "score": score,
#                 }
#             )

#     except Exception as e:

#         print(
#             f"Parser error: "
#             f"{type(e).__name__}: {e}"
#         )

#         return ""

#     if not parsed_items:

#         print(
#             "No valid OCR text found."
#         )

#         return ""

#     # --------------------------------------------------------
#     # Sort vertically
#     # --------------------------------------------------------

#     parsed_items.sort(
#         key=lambda item:
#         item["y_center"]
#     )

#     lines = []

#     current_line = []

#     current_y = None

#     for item in parsed_items:

#         if (
#             current_y is None
#             or abs(
#                 item["y_center"]
#                 - current_y
#             ) <= y_tolerance
#         ):

#             current_line.append(item)

#             current_y = float(
#                 np.mean(
#                     [
#                         x["y_center"]
#                         for x in current_line
#                     ]
#                 )
#             )

#         else:

#             current_line.sort(
#                 key=lambda x: x["x"]
#             )

#             lines.append(
#                 "   ".join(
#                     x["text"]
#                     for x in current_line
#                 )
#             )

#             current_line = [item]

#             current_y = item["y_center"]

#     # --------------------------------------------------------
#     # Last line
#     # --------------------------------------------------------

#     if current_line:

#         current_line.sort(
#             key=lambda x: x["x"]
#         )

#         lines.append(
#             "   ".join(
#                 x["text"]
#                 for x in current_line
#             )
#         )

#     result = "\n".join(lines)

#     print(
#         f"Extracted {len(lines)} lines."
#     )

#     return result


# # ============================================================
# # Main OCR function
# # ============================================================

# def extract_best_text(images: dict) -> str:

#     preferred_images = [
#         images.get("original"),
#         images.get("gray"),
#         images.get("threshold"),
#     ]

#     ocr_engine = get_ocr()

#     for path in preferred_images:

#         if not path:
#             continue

#         if not os.path.exists(path):

#             print(
#                 f"Image does not exist: {path}"
#             )

#             continue

#         try:

#             print(
#                 f"\nRunning OCR on: {path}"
#             )

#             # ------------------------------------------------
#             # Resize large image
#             # ------------------------------------------------

#             ocr_path = prepare_image(
#                 path
#             )

#             print(
#                 "Starting PaddleOCR..."
#             )

#             predict = getattr(ocr_engine, "predict", None)
#             if callable(predict):
#                 raw_result = list(predict(ocr_path))
#             else:
#                 raw_result = ocr_engine.ocr(ocr_path, cls=False)

#             print(
#                 "PaddleOCR recognition finished."
#             )

#             if not raw_result:

#                 print(
#                     "PaddleOCR returned empty result."
#                 )

#                 continue

#             if not raw_result[0]:

#                 print(
#                     "PaddleOCR returned no text."
#                 )

#                 continue

#             print(
#                 "Parsing OCR result..."
#             )

#             text = parse_receipt_boxes(
#                 raw_result,
#                 y_tolerance=12,
#                 min_score=0.55,
#             )

#             if text.strip():

#                 print(
#                     "OCR extraction successful."
#                 )

#                 return text

#             print(
#                 "OCR returned no usable text."
#             )

#         except Exception as e:

#             print(
#                 "\nOCR ERROR:"
#             )

#             print(
#                 f"{type(e).__name__}: {e}"
#             )

#             continue

#     print(
#         "OCR failed for all image variants."
#     )

#     return ""


import os
import cv2
import numpy as np
from paddleocr import PaddleOCR


# ============================================================
# Global OCR instance
# ============================================================

ocr = None


# ============================================================
# Initialize PaddleOCR
# ============================================================

def get_ocr():
    global ocr

    if ocr is None:
        print("Initializing PaddleOCR...")

        ocr = PaddleOCR(
            lang="en",
            enable_mkldnn=False,
            cpu_threads=1,
            rec_batch_num=1,
            det_limit_side_len=960,
            det_limit_type="max",
        )

        print("PaddleOCR initialized successfully.")

    return ocr


# ============================================================
# Resize image
# ============================================================

def prepare_image(path, max_width=1600, max_height=2200):

    print(f"Preparing image: {path}")

    image = cv2.imread(path)

    if image is None:
        raise ValueError(f"Could not read image: {path}")

    height, width = image.shape[:2]

    print(f"Original image size: {width}x{height}")

    if width <= max_width and height <= max_height:
        print("Image resize not required.")
        return path

    scale = min(
        max_width / width,
        max_height / height
    )

    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))

    resized = cv2.resize(
        image,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA
    )

    directory = os.path.dirname(path)
    filename = os.path.basename(path)

    name, ext = os.path.splitext(filename)

    resized_path = os.path.join(
        directory,
        f"{name}_ocr{ext}"
    )

    cv2.imwrite(resized_path, resized)

    print(f"Resized image: {new_width}x{new_height}")
    print(f"OCR image: {resized_path}")

    return resized_path


# ============================================================
# Extract from NEW PaddleOCR result
# ============================================================

def parse_new_result(result):

    texts = []
    scores = []

    # ---------------------------------------------
    # Case 1: dictionary
    # ---------------------------------------------

    if isinstance(result, dict):

        texts = result.get("rec_texts", [])
        scores = result.get("rec_scores", [])

    # ---------------------------------------------
    # Case 2: PaddleOCR OCRResult object
    # ---------------------------------------------

    else:

        try:
            texts = getattr(result, "rec_texts", [])
            scores = getattr(result, "rec_scores", [])
        except Exception:
            texts = []
            scores = []

    if texts is None:
        texts = []

    if scores is None:
        scores = []

    print(f"Recognition texts found: {len(texts)}")

    output = []

    for i, text in enumerate(texts):

        text = str(text).strip()

        if not text:
            continue

        score = 1.0

        if i < len(scores):
            try:
                score = float(scores[i])
            except Exception:
                score = 1.0

        if score < 0.40:
            continue

        output.append(text)

    return output


# ============================================================
# Extract from OLD PaddleOCR result
# ============================================================

def parse_old_result(result):

    output = []

    if not result:
        return output

    try:

        # Typical PaddleOCR 2.x format:
        #
        # [
        #   [
        #       [box, ("text", score)],
        #       [box, ("text", score)]
        #   ]
        # ]

        pages = result

        if isinstance(pages, list) and len(pages) > 0:

            page = pages[0]

            if isinstance(page, list):

                for item in page:

                    if not item or len(item) < 2:
                        continue

                    box = item[0]
                    text_info = item[1]

                    if not text_info or len(text_info) < 2:
                        continue

                    text = str(text_info[0]).strip()

                    try:
                        score = float(text_info[1])
                    except Exception:
                        score = 1.0

                    if not text:
                        continue

                    if score < 0.40:
                        continue

                    # Keep position for line ordering
                    x = 0
                    y = 0

                    try:
                        x = min(point[0] for point in box)
                        y = min(point[1] for point in box)
                    except Exception:
                        pass

                    output.append({
                        "text": text,
                        "x": x,
                        "y": y,
                        "score": score
                    })

    except Exception as e:

        print(
            f"Old OCR parser error: "
            f"{type(e).__name__}: {e}"
        )

        return []

    # --------------------------------------------------------
    # Sort into reading order
    # --------------------------------------------------------

    if not output:
        return []

    output.sort(key=lambda item: item["y"])

    lines = []

    current_line = []
    current_y = None

    y_tolerance = 15

    for item in output:

        if (
            current_y is None
            or abs(item["y"] - current_y) <= y_tolerance
        ):

            current_line.append(item)

            current_y = sum(
                x["y"] for x in current_line
            ) / len(current_line)

        else:

            current_line.sort(
                key=lambda x: x["x"]
            )

            lines.append(
                "   ".join(
                    x["text"]
                    for x in current_line
                )
            )

            current_line = [item]
            current_y = item["y"]

    if current_line:

        current_line.sort(
            key=lambda x: x["x"]
        )

        lines.append(
            "   ".join(
                x["text"]
                for x in current_line
            )
        )

    return lines


# ============================================================
# Parse PaddleOCR result
# ============================================================

def parse_ocr_result(raw_result):

    if not raw_result:
        print("OCR result is empty.")
        return ""

    print(
        "OCR result type:",
        type(raw_result)
    )

    try:

        # ----------------------------------------------------
        # New PaddleOCR predict() result
        # ----------------------------------------------------

        if not isinstance(raw_result, list):

            texts = parse_new_result(raw_result)

            if texts:
                return "\n".join(texts)

        # ----------------------------------------------------
        # List result
        # ----------------------------------------------------

        if isinstance(raw_result, list):

            if len(raw_result) == 0:
                return ""

            # New API may return a list of OCRResult objects
            first = raw_result[0]

            if not isinstance(first, (list, tuple, dict)):

                texts = parse_new_result(first)

                if texts:
                    return "\n".join(texts)

            # Old API
            lines = parse_old_result(raw_result)

            if lines:
                return "\n".join(lines)

            # Sometimes new API returns dictionaries in a list
            if isinstance(first, dict):

                texts = parse_new_result(first)

                if texts:
                    return "\n".join(texts)

    except Exception as e:

        print(
            f"OCR parsing error: "
            f"{type(e).__name__}: {e}"
        )

    return ""


# ============================================================
# Main OCR function
# ============================================================

def extract_best_text(images: dict) -> str:

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

            print(f"Image does not exist: {path}")
            continue

        try:

            print(f"\nRunning OCR on: {path}")

            # ------------------------------------------------
            # Resize image
            # ------------------------------------------------

            ocr_path = prepare_image(path)

            print("Starting PaddleOCR...")

            # ------------------------------------------------
            # IMPORTANT
            #
            # Try the legacy OCR API first.
            # This matches PaddleOCR 2.x.
            # ------------------------------------------------

            raw_result = None

            try:

                raw_result = ocr_engine.ocr(
                    ocr_path,
                    cls=False
                )

                print("PaddleOCR .ocr() completed.")

            except Exception as old_api_error:

                print(
                    "Legacy .ocr() failed:",
                    type(old_api_error).__name__,
                    str(old_api_error)
                )

                # ------------------------------------------------
                # Fallback to new predict API
                # ------------------------------------------------

                predict = getattr(
                    ocr_engine,
                    "predict",
                    None
                )

                if not callable(predict):
                    raise old_api_error

                print("Trying PaddleOCR .predict()...")

                raw_result = list(
                    predict(ocr_path)
                )

                print(
                    "PaddleOCR .predict() completed."
                )

            # ------------------------------------------------
            # Parse result
            # ------------------------------------------------

            print("Parsing OCR result...")

            text = parse_ocr_result(raw_result)

            print(
                f"Extracted OCR characters: {len(text)}"
            )

            if text.strip():

                print(
                    "OCR extraction successful."
                )

                print(
                    "----- OCR TEXT PREVIEW -----"
                )

                print(
                    text[:1000]
                )

                print(
                    "-----------------------------"
                )

                return text

            print(
                "OCR returned no usable text."
            )

        except Exception as e:

            print(
                "\nOCR ERROR:"
            )

            print(
                f"{type(e).__name__}: {e}"
            )

            continue

    print(
        "OCR failed for all image variants."
    )

    return ""