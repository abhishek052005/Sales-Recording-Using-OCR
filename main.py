import asyncio
import json
import os
import shutil
import uvicorn

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from preprocessing.preprocess import preprocess_image
from ocr.ocr_engine import extract_best_text
from extraction.extractor import extract_invoice_data
from local_store import check_filename, find_duplicate_invoice, get_all_invoices, save_invoice
from pdf_utils import convert_pdf_to_images

app = FastAPI(title="Invoice OCR Backend")

# ==========================================
# CORS MIDDLEWARE (NFR-3 Security)
# ==========================================


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from any origin    
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Server Error: {str(exc)}"}
    )


# ==========================================
# FOLDERS
# ==========================================

UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
OCR_OUTPUT_FOLDER = "ocr_output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(OCR_OUTPUT_FOLDER, exist_ok=True)

# ==========================================
# HOME ENDPOINT
# ==========================================

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/",response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
    request=request, 
    name="index.html", 
    context={"title": "Home"}  # Pass additional context here if needed
)

# ==========================================
# UPLOAD INVOICE 
# ==========================================

def process_invoice(file: UploadFile):
    allowed_extensions = ["jpg", "jpeg", "png", "pdf"]

    if not file.filename:
        raise ValueError("Filename is missing.")

    extension = file.filename.split(".")[-1].lower()
    if extension not in allowed_extensions:
        raise ValueError("Only JPG, JPEG, PNG, and PDF files are allowed.")

    if check_filename(file.filename):
        raise ValueError(
            f"You have already uploaded a file named '{file.filename}'. "
            "Please use a different filename or delete the existing file first."
        )

    upload_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if extension == "pdf":
        input_image_paths = convert_pdf_to_images(upload_path, UPLOAD_FOLDER)
    else:
        input_image_paths = [upload_path]

    all_page_ocr_texts = []
    for img_path in input_image_paths:
        img_filename = os.path.basename(img_path)
        processed_path = os.path.join(PROCESSED_FOLDER, img_filename)
        processed_images = preprocess_image(img_path, processed_path)
        page_text = extract_best_text(processed_images)
        if page_text and page_text.strip():
            all_page_ocr_texts.append(page_text.strip())

    combined_ocr_text = "\n\n--- Page Separator ---\n\n".join(all_page_ocr_texts)
    if not combined_ocr_text.strip():
        raise ValueError("OCR could not extract text from document.")

    output_file = os.path.join(OCR_OUTPUT_FOLDER, f"{file.filename}.txt")
    with open(output_file, "w", encoding="utf-8") as output:
        output.write(combined_ocr_text)

    invoice_data = extract_invoice_data(combined_ocr_text)
    duplicate_invoice = find_duplicate_invoice(
        invoice_number=invoice_data.get("invoice_number"),
        vendor_name=invoice_data.get("vendor", {}).get("name"),
        invoice_date=invoice_data.get("invoice_date"),
        total=invoice_data.get("total"),
    )

    return {
        "message": "Success",
        "filename": file.filename,
        "ocr_text": combined_ocr_text,
        "invoice_data": invoice_data,
        "duplicate_detected": bool(duplicate_invoice),
        "duplicate_invoice": duplicate_invoice,
    }

# @app.post("/upload")
# async def upload_file(file: UploadFile = File(...)):
#     contents = await file.read()

#     return {
#         "filename": file.filename,
#         "size": len(contents),
#         "message": "Upload works"
#     }
@app.post("/upload")
async def upload_invoice(files: list[UploadFile] = File(...)):
    async def stream_results():
        for file in files:
            task = asyncio.create_task(asyncio.to_thread(process_invoice, file))
            yield json.dumps({
                "type": "progress",
                "filename": file.filename or "unknown file",
            }) + "\n"

            try:
                while not task.done():
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(task),
                            timeout=15,
                        )
                    except asyncio.TimeoutError:
                        yield json.dumps({
                            "type": "progress",
                            "filename": file.filename or "unknown file",
                        }) + "\n"

                result = await task
                yield json.dumps({"type": "invoice", "result": result}) + "\n"
            except Exception as error:
                yield json.dumps({
                    "type": "error",
                    "filename": file.filename or "unknown file",
                    "error": str(error),
                }) + "\n"

    return StreamingResponse(
        stream_results(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache"},
    )




# ==========================================
# SAVE REVIEWED INVOICE 
# ==========================================

@app.post("/save-review")
async def save_review(
    data: dict,
):
    filename = data.get("filename")
    ocr_text = data.get("ocr_text")
    invoice_data = data.get("invoice_data")

    if not filename:
        return JSONResponse(
            status_code=400,
            content={"error": "Filename is required."}
        )

    if not invoice_data:
        return JSONResponse(
            status_code=400,
            content={"error": "Invoice data is required."}
        )

    duplicate_invoice = find_duplicate_invoice(
        invoice_number=invoice_data.get("invoice_number"),
        vendor_name=invoice_data.get("vendor", {}).get("name"),
        invoice_date=invoice_data.get("invoice_date"),
        total=invoice_data.get("total"),
    )

    if duplicate_invoice:
        return JSONResponse(
            status_code=409,
            content={
                "error": "Duplicate invoice detected.",
                "duplicate_detected": True,
                "duplicate_invoice": duplicate_invoice,
            }
        )

    document_id = save_invoice(
        filename=filename,
        ocr_text=ocr_text or "",
        invoice_data=invoice_data,
    )

    return {
        "message": "Invoice saved successfully",
        "document_id": document_id,
        "filename": filename
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/invoices")
def get_invoices():
    """Get all locally saved invoices."""
    return {"items": get_all_invoices()}

# ==========================================
# RUN SERVER
# ==========================================
# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port
    )



