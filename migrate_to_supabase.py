"""
Supabase PostgreSQL Database Initializer
Creates users, invoices, and invoice_items tables in your Supabase project.
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

def init_supabase_db():
    print("==================================================")
    print("      SUPABASE POSTGRESQL DATABASE INITIALIZER     ")
    print("==================================================")
    
    db_url = os.getenv("DATABASE_URL")
    print(f"\n[1] Checking Configured Database URL:")
    print(f"    {db_url}")

    if not db_url or "YOUR_SUPABASE_DB_PASSWORD" in db_url:
        print("\n[!] ACTION REQUIRED:")
        print("    Please set your database password in the .env file.")
        print("    Example:")
        print("    DATABASE_URL=postgresql+psycopg2://postgres:<PASSWORD>@db.iwopapapccvxuczfwwtx.supabase.co:5432/postgres")
        return False

    print("\n[2] Connecting to Supabase PostgreSQL & Initializing Tables...")
    try:
        from database import Base, engine, create_tables
        create_tables()
        print("    [OK] Table 'users' initialized successfully.")
        print("    [OK] Table 'invoices' initialized successfully.")
        print("    [OK] Table 'invoice_items' initialized successfully.")
        print("\n[+] SUCCESS: Supabase PostgreSQL is fully ready and connected!")
        return True
    except Exception as e:
        print(f"    [X] Connection Failed: {e}")
        return False

if __name__ == "__main__":
    init_supabase_db()
