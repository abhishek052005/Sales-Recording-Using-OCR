import json
import os
from datetime import datetime, timezone
from threading import Lock


STORE_PATH = "saved_invoices.json"
_store_lock = Lock()


def _read_invoices() -> list[dict]:
    if not os.path.exists(STORE_PATH):
        return []

    with open(STORE_PATH, "r", encoding="utf-8") as store_file:
        data = json.load(store_file)
    return data if isinstance(data, list) else []


def _write_invoices(invoices: list[dict]) -> None:
    temporary_path = f"{STORE_PATH}.tmp"
    with open(temporary_path, "w", encoding="utf-8") as store_file:
        json.dump(invoices, store_file, ensure_ascii=True, indent=2)
    os.replace(temporary_path, STORE_PATH)


def find_duplicate_invoice(
    invoice_number: str | None = None,
    vendor_name: str | None = None,
    invoice_date: str | None = None,
    total: float | None = None,
) -> dict | None:
    normalized_number = invoice_number.strip().lower() if invoice_number else None
    normalized_vendor = vendor_name.strip().lower() if vendor_name else None
    normalized_date = invoice_date.strip().lower() if invoice_date else None

    with _store_lock:
        invoices = _read_invoices()

    for invoice in reversed(invoices):
        stored_number = invoice.get("invoice_number")
        stored_vendor = invoice.get("vendor_name")
        stored_date = invoice.get("invoice_date")
        stored_total = invoice.get("total")

        if normalized_number and normalized_vendor:
            matches = (
                isinstance(stored_number, str)
                and stored_number.strip().lower() == normalized_number
                and isinstance(stored_vendor, str)
                and stored_vendor.strip().lower() == normalized_vendor
            )
        elif normalized_number and normalized_date:
            matches = (
                isinstance(stored_number, str)
                and stored_number.strip().lower() == normalized_number
                and isinstance(stored_date, str)
                and stored_date.strip().lower() == normalized_date
            )
        elif normalized_vendor and normalized_date and total is not None:
            matches = (
                isinstance(stored_vendor, str)
                and stored_vendor.strip().lower() == normalized_vendor
                and isinstance(stored_date, str)
                and stored_date.strip().lower() == normalized_date
                and stored_total == total
            )
        else:
            matches = False

        if matches:
            return invoice

    return None


def check_filename(filename: str) -> bool:
    with _store_lock:
        return any(invoice.get("filename") == filename for invoice in _read_invoices())


def save_invoice(filename: str, ocr_text: str, invoice_data: dict) -> int:
    vendor = invoice_data.get("vendor", {})
    customer = invoice_data.get("customer", {})

    with _store_lock:
        invoices = _read_invoices()
        next_id = max((invoice.get("id", 0) for invoice in invoices), default=0) + 1
        saved_invoice = {
            "id": next_id,
            "filename": filename,
            "invoice_number": invoice_data.get("invoice_number"),
            "invoice_date": invoice_data.get("invoice_date"),
            "vendor_name": vendor.get("name"),
            "vendor_gstin": vendor.get("gstin"),
            "customer_name": customer.get("name"),
            "customer_gstin": customer.get("gstin"),
            "subtotal": invoice_data.get("subtotal"),
            "tax": invoice_data.get("tax"),
            "total": invoice_data.get("total"),
            "currency": invoice_data.get("currency"),
            "raw_ocr_text": ocr_text,
            "items": invoice_data.get("items", []),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        invoices.append(saved_invoice)
        _write_invoices(invoices)

    return next_id


def get_all_invoices() -> list[dict]:
    with _store_lock:
        invoices = _read_invoices()
    return list(reversed(invoices))