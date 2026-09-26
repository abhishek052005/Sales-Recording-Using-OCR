import cv2
import numpy as np
import os


def deskew(image):
    """Automatically straighten the image"""

    sample_scale = min(1.0, 1000 / max(image.shape[:2]))
    if sample_scale < 1.0:
        sample = cv2.resize(
            image,
            None,
            fx=sample_scale,
            fy=sample_scale,
            interpolation=cv2.INTER_AREA
        )
    else:
        sample = image

    coords = np.column_stack(np.where(sample < 255))

    if len(coords) == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = 90 + angle

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)

    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    rotated = cv2.warpAffine(
        image,
        M,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    return rotated


def preprocess_image(input_path, output_path):

    image = cv2.imread(input_path)

    if image is None:
        raise Exception(f"Cannot read image : {input_path}")

    # -----------------------
    # Resize
    # -----------------------
    scale = min(2.0, 2400 / max(image.shape[:2]))
    image = cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC if scale >= 1 else cv2.INTER_AREA
    )

    original_path = os.path.splitext(output_path)[0] + "_original.png"
    cv2.imwrite(original_path, image)

    # -----------------------
    # Gray
    # -----------------------
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # -----------------------
    # CLAHE
    # -----------------------
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    gray = clahe.apply(gray)

    # -----------------------
    # Denoise
    # -----------------------
    gray = cv2.fastNlMeansDenoising(
        gray,
        None,
        h=12
    )

    # -----------------------
    # Sharpen
    # -----------------------
    kernel = np.array([
        [0,-1,0],
        [-1,5,-1],
        [0,-1,0]
    ])

    gray = cv2.filter2D(gray,-1,kernel)

    # -----------------------
    # Threshold
    # -----------------------
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        8
    )

    # -----------------------
    # Morphology
    # -----------------------
    kernel = np.ones((2,2),np.uint8)

    thresh = cv2.morphologyEx(
        thresh,
        cv2.MORPH_OPEN,
        kernel
    )

    thresh = cv2.dilate(
        thresh,
        kernel,
        iterations=1
    )

    # -----------------------
    # Deskew
    # -----------------------
    thresh = deskew(thresh)
    gray = deskew(gray)

    # -----------------------
    # File Names
    # -----------------------
    base = os.path.splitext(output_path)[0]

    threshold_path = base + "_thresh.png"
    gray_path = base + "_gray.png"

    cv2.imwrite(threshold_path, thresh)
    cv2.imwrite(gray_path, gray)

    print("Gray Image :", gray_path)
    print("Threshold :", threshold_path)

    return {
        "gray": gray_path,
        "threshold": threshold_path,
        "original": original_path
    }
