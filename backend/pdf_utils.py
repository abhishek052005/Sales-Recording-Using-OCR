import os
import shutil
from typing import List
from pdf2image import convert_from_path

POPPLER_PATH = os.environ.get("POPPLER_PATH")


def _find_poppler_path() -> str | None:
    """Return the valid Poppler bin folder path or None if not found."""
    if POPPLER_PATH and os.path.isdir(POPPLER_PATH):
        if shutil.which("pdftoppm", path=POPPLER_PATH) or shutil.which("pdfinfo", path=POPPLER_PATH):
            return POPPLER_PATH

    for executable in ("pdftoppm", "pdfinfo", "pdftoppm.exe", "pdfinfo.exe"):
        exe_path = shutil.which(executable)
        if exe_path:
            return os.path.dirname(exe_path)

    return None


def convert_pdf_to_images(pdf_path: str, output_folder: str) -> List[str]:
    base_filename = os.path.splitext(os.path.basename(pdf_path))[0]

    poppler_path = _find_poppler_path()
    if poppler_path is None:
        raise EnvironmentError(
            "Poppler not found. Install Poppler and ensure 'pdftoppm' is on PATH, or set POPPLER_PATH "
            "in the deployment environment."
        )

    images = convert_from_path(pdf_path, poppler_path=poppler_path)

    image_paths = []
    os.makedirs(output_folder, exist_ok=True)  # Ensure destination folder exists

    for i, image in enumerate(images):
        image_filename = f"{base_filename}_page_{i + 1}.jpg"
        image_path = os.path.join(output_folder, image_filename)
        image.save(image_path, "JPEG")
        image_paths.append(image_path)

    return image_paths