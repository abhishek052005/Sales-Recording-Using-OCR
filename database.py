import os
from datetime import datetime, timezone
from typing import List, Optional

from dotenv import load_dotenv
from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint, create_engine, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing in .env")

# Normalize PostgreSQL driver prefix for SQLAlchemy (e.g. postgres:// or postgresql:// -> postgresql+psycopg2://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)


# ==========================================
# SUPABASE POSTGRESQL CONNECTION & BASE
# ==========================================

# Configure SQLAlchemy engine with connection pool pre-ping for remote databases
engine_kwargs = {"pool_pre_ping": True}
if "sqlite" not in DATABASE_URL:
    engine_kwargs.update({"pool_size": 10, "max_overflow": 20})

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

# Optional Supabase Client initialization using API keys
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

supabase_client = None
if SUPABASE_URL and SUPABASE_SECRET_KEY:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
    except Exception as e:
        print(f"Warning: Supabase SDK client initialization skipped: {e}")



class Base(DeclarativeBase):
    pass


# ==========================================
# USER TABLE (NFR-3 Authentication)
# ==========================================

class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    invoices: Mapped[List["InvoiceDB"]] = relationship(back_populates="owner")


# ==========================================
# INVOICE TABLE
# ==========================================

class InvoiceDB(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100))
    invoice_date: Mapped[Optional[str]] = mapped_column(String(20))

    # Owner linkage for tenancy isolation (NFR-3)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    owner: Mapped[Optional["UserDB"]] = relationship(back_populates="invoices")

    # Vendor
    vendor_name: Mapped[Optional[str]] = mapped_column(String(255))
    vendor_gstin: Mapped[Optional[str]] = mapped_column(String(50))
    vendor_address: Mapped[Optional[str]] = mapped_column(Text)
    vendor_phone: Mapped[Optional[str]] = mapped_column(String(50))
    vendor_email: Mapped[Optional[str]] = mapped_column(String(255))

    # Customer
    customer_name: Mapped[Optional[str]] = mapped_column(String(255))
    customer_gstin: Mapped[Optional[str]] = mapped_column(String(50))
    customer_address: Mapped[Optional[str]] = mapped_column(Text)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(50))
    customer_email: Mapped[Optional[str]] = mapped_column(String(255))

    # Totals
    subtotal: Mapped[Optional[float]] = mapped_column(Float)
    tax: Mapped[Optional[float]] = mapped_column(Float)
    total: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[Optional[str]] = mapped_column(String(10))

    # OCR
    raw_ocr_text: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    # Items relationship
    items: Mapped[List["InvoiceItemDB"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )

    # Composite unique constraint: each user can only have one invoice per filename
    __table_args__ = (
        UniqueConstraint('user_id', 'filename', name='uq_user_filename'),
    )


# ==========================================
# INVOICE ITEMS TABLE
# ==========================================

class InvoiceItemDB(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    unit_price: Mapped[Optional[float]] = mapped_column(Float)
    tax_rate: Mapped[Optional[float]] = mapped_column(Float)
    amount: Mapped[Optional[float]] = mapped_column(Float)

    invoice: Mapped["InvoiceDB"] = relationship(back_populates="items")


# ==========================================
# CREATE TABLES
# ==========================================

def create_tables():
    if "YOUR_SUPABASE_DB_PASSWORD" in DATABASE_URL:
        print("[!] NOTICE: Supabase database password is not configured in .env yet.")
        print("[!] Please update DATABASE_URL in .env with your actual password and run 'migrate_to_supabase.py'.")
        return

    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] Supabase database tables verified/created successfully.")
    except Exception as e:
        print(f"[!] Warning: Could not auto-create database tables on startup: {e}")
        print("[!] Ensure your database password in .env is correct and Supabase project is active.")



# ==========================================
# USER AUTHENTICATION FUNCTIONS (NFR-3)
# ==========================================

def create_user(username: str, hashed_password: str, role: str = "user") -> int:
    """Create a new user with hashed password."""
    db = SessionLocal()
    try:
        user = UserDB(
            username=username,
            hashed_password=hashed_password,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_user_by_username(username: str) -> Optional[UserDB]:
    """Retrieve user by username for authentication."""
    db = SessionLocal()
    try:
        return db.query(UserDB).filter(UserDB.username == username).first()
    finally:
        db.close()


# ==========================================
# GET ALL INVOICES
# ==========================================

def get_all_invoices(user_id: Optional[int] = None, is_admin: bool = False) -> list[dict]:
    """Get invoices with access control (NFR-3)."""
    db = SessionLocal()
    try:
        query = db.query(InvoiceDB)
        if not is_admin and user_id is not None:
            # Non-admin users can only see their own invoices
            query = query.filter(InvoiceDB.user_id == user_id)

        invoices = query.order_by(InvoiceDB.created_at.desc(), InvoiceDB.id.desc()).all()

        return [
            {
                "id": invoice.id,
                "filename": invoice.filename,
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date,
                "vendor_name": invoice.vendor_name,
                "vendor_gstin": invoice.vendor_gstin,
                "customer_name": invoice.customer_name,
                "customer_gstin": invoice.customer_gstin,
                "subtotal": invoice.subtotal,
                "tax": invoice.tax,
                "total": invoice.total,
                "currency": invoice.currency,
                "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
            }
            for invoice in invoices
        ]
    finally:
        db.close()


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()
    return normalized or None


def _invoice_summary(invoice: InvoiceDB) -> dict:
    return {
        "id": invoice.id,
        "filename": invoice.filename,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date,
        "vendor_name": invoice.vendor_name,
        "subtotal": invoice.subtotal,
        "tax": invoice.tax,
        "total": invoice.total,
        "currency": invoice.currency,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
    }


def find_duplicate_invoice(
    invoice_number: str | None = None,
    vendor_name: str | None = None,
    invoice_date: str | None = None,
    total: float | None = None,
) -> dict | None:
    db = SessionLocal()
    try:
        normalized_invoice_number = _normalize_text(invoice_number)
        normalized_vendor_name = _normalize_text(vendor_name)
        normalized_invoice_date = _normalize_text(invoice_date)

        query = db.query(InvoiceDB)

        if normalized_invoice_number and normalized_vendor_name:
            query = query.filter(
                func.lower(func.trim(InvoiceDB.invoice_number)) == normalized_invoice_number,
                func.lower(func.trim(InvoiceDB.vendor_name)) == normalized_vendor_name,
            )
        elif normalized_invoice_number and normalized_invoice_date:
            query = query.filter(
                func.lower(func.trim(InvoiceDB.invoice_number)) == normalized_invoice_number,
                func.lower(func.trim(InvoiceDB.invoice_date)) == normalized_invoice_date,
            )
        elif normalized_vendor_name and normalized_invoice_date and total is not None:
            query = query.filter(
                func.lower(func.trim(InvoiceDB.vendor_name)) == normalized_vendor_name,
                func.lower(func.trim(InvoiceDB.invoice_date)) == normalized_invoice_date,
                InvoiceDB.total == total,
            )
        else:
            return None

        duplicate = query.order_by(InvoiceDB.created_at.desc(), InvoiceDB.id.desc()).first()
        if duplicate:
            return _invoice_summary(duplicate)

        return None
    finally:
        db.close()


def check_filename_for_user(filename: str, user_id: int) -> bool:
    """
    Check if a filename already exists for the given user.
    Returns True if duplicate filename exists, False otherwise.
    """
    db = SessionLocal()
    try:
        existing = (
            db.query(InvoiceDB)
            .filter(InvoiceDB.user_id == user_id, InvoiceDB.filename == filename)
            .first()
        )
        return existing is not None
    finally:
        db.close()


# ==========================================
# SAVE INVOICE
# ==========================================

def save_invoice(filename: str, ocr_text: str, invoice_data: dict, user_id: int) -> int:
    """Save invoice data with user ownership (NFR-3 Access Control)."""
    db = SessionLocal()
    try:
        vendor = invoice_data.get("vendor", {})
        customer = invoice_data.get("customer", {})

        invoice = InvoiceDB(
            filename=filename,
            user_id=user_id,
            invoice_number=invoice_data.get("invoice_number"),
            invoice_date=invoice_data.get("invoice_date"),
            vendor_name=vendor.get("name"),
            vendor_gstin=vendor.get("gstin"),
            vendor_address=vendor.get("address"),
            vendor_phone=vendor.get("phone"),
            vendor_email=vendor.get("email"),
            customer_name=customer.get("name"),
            customer_gstin=customer.get("gstin"),
            customer_address=customer.get("address"),
            customer_phone=customer.get("phone"),
            customer_email=customer.get("email"),
            subtotal=invoice_data.get("subtotal"),
            tax=invoice_data.get("tax"),
            total=invoice_data.get("total"),
            currency=invoice_data.get("currency"),
            raw_ocr_text=ocr_text,
        )

        items = invoice_data.get("items", [])
        for item in items:
            invoice_item = InvoiceItemDB(
                description=item.get("description", ""),
                quantity=item.get("quantity"),
                unit_price=item.get("unit_price"),
                tax_rate=item.get("tax_rate"),
                amount=item.get("amount"),
            )
            invoice.items.append(invoice_item)

        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        return invoice.id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


