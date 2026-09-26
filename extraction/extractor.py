import json
import os

from dotenv import load_dotenv
from google import genai

from .models import Invoice


load_dotenv()

client = None


SYSTEM_PROMPT = """
You are an invoice data extraction system.

Extract structured invoice information from the OCR text.

Rules:
1. Extract only information present in the OCR text.
2. Never invent or guess information.
3. Use null when information is missing.
4. Extract all identifiable invoice items.
5. Numbers must be returned as numbers.
6. Normalize dates to YYYY-MM-DD when possible.
7. Preserve GSTIN exactly as found.
8. Correct obvious OCR errors only when the intended value is clear.
9. Do not calculate missing values.
10. Return only the requested JSON structure.
"""


def get_invoice_schema():

    return {
        "type": "object",

        "properties": {

            "invoice_number": {
                "type": ["string", "null"]
            },

            "invoice_date": {
                "type": ["string", "null"]
            },

            "vendor": {
                "type": "object",

                "properties": {
                    "name": {
                        "type": ["string", "null"]
                    },
                    "gstin": {
                        "type": ["string", "null"]
                    },
                    "address": {
                        "type": ["string", "null"]
                    },
                    "phone": {
                        "type": ["string", "null"]
                    },
                    "email": {
                        "type": ["string", "null"]
                    }
                },

                "required": [
                    "name",
                    "gstin",
                    "address",
                    "phone",
                    "email"
                ],

                "additionalProperties": False
            },

            "customer": {
                "type": "object",

                "properties": {
                    "name": {
                        "type": ["string", "null"]
                    },
                    "gstin": {
                        "type": ["string", "null"]
                    },
                    "address": {
                        "type": ["string", "null"]
                    },
                    "phone": {
                        "type": ["string", "null"]
                    },
                    "email": {
                        "type": ["string", "null"]
                    }
                },

                "required": [
                    "name",
                    "gstin",
                    "address",
                    "phone",
                    "email"
                ],

                "additionalProperties": False
            },

            "items": {
                "type": "array",

                "items": {
                    "type": "object",

                    "properties": {
                        "description": {
                            "type": "string"
                        },
                        "quantity": {
                            "type": ["number", "null"]
                        },
                        "unit_price": {
                            "type": ["number", "null"]
                        },
                        "tax_rate": {
                            "type": ["number", "null"]
                        },
                        "amount": {
                            "type": ["number", "null"]
                        }
                    },

                    "required": [
                        "description",
                        "quantity",
                        "unit_price",
                        "tax_rate",
                        "amount"
                    ],

                    "additionalProperties": False
                }
            },

            "subtotal": {
                "type": ["number", "null"]
            },

            "tax": {
                "type": ["number", "null"]
            },

            "total": {
                "type": ["number", "null"]
            },

            "currency": {
                "type": ["string", "null"]
            }
        },

        "required": [
            "invoice_number",
            "invoice_date",
            "vendor",
            "customer",
            "items",
            "subtotal",
            "tax",
            "total",
            "currency"
        ],

        "additionalProperties": False
    }


def get_gemini_schema(schema):
    if isinstance(schema, list):
        return [get_gemini_schema(item) for item in schema]

    if not isinstance(schema, dict):
        return schema

    converted = {
        key: get_gemini_schema(value)
        for key, value in schema.items()
        if key not in {"type", "additionalProperties"}
    }
    schema_type = schema.get("type")

    if isinstance(schema_type, list):
        non_null_type = next(
            item for item in schema_type if item != "null"
        )
        converted["type"] = non_null_type.upper()
        converted["nullable"] = True
    elif isinstance(schema_type, str):
        converted["type"] = schema_type.upper()

    return converted


def extract_invoice_data(ocr_text: str):

    if not ocr_text or not ocr_text.strip():
        raise ValueError("OCR text is empty")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    global client
    if client is None:
        client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        contents=f"""
Extract invoice data from this OCR text:

-------------------------
{ocr_text}
-------------------------
"""
        ,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "temperature": 0,
            "max_output_tokens": 4096,
            "response_mime_type": "application/json",
            "response_schema": get_gemini_schema(get_invoice_schema()),
        },
    )

    content = response.text

    if not content:
        raise ValueError("Gemini returned an empty response")

    try:
        data = json.loads(content)

    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON returned by Gemini: {e}"
        )

    # Pydantic validation
    invoice = Invoice.model_validate(data)

    # Return normal Python dict to FastAPI
    return invoice.model_dump()
