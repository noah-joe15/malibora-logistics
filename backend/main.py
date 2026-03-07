from fastapi import FastAPI, Depends, HTTPException, Security, status, File, UploadFile
from fastapi.security.api_key import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os
import shutil

app = FastAPI()

# ---------------------------------------------------------
# DATABASE SETUP: The Supabase Brain
# ---------------------------------------------------------
DATABASE_URL = "postgresql://postgres.yzvjutqqujbpvalelbld:jorsavantcally15@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"
engine = create_engine(DATABASE_URL)

@app.get("/test-db")
def test_database():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT version();"))
            return {"status": "SUCCESS!", "message": "The Supabase Brain is officially online."}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

# ---------------------------------------------------------
# MIDDLEWARE & FOLDER SETUP
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
UPLOAD_DIR = os.path.join(PUBLIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------
# SECURITY: API Key Authentication
# ---------------------------------------------------------
API_KEY = "MALIBORA_SECRET_KEY_2026"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(status_code=403, detail="Access Denied")

# ---------------------------------------------------------
# DATA MODELS (Now with company_id and Auth!)
# ---------------------------------------------------------
class CompanyAuth(BaseModel):
    company_name: str
    admin_pin: str

class Truck(BaseModel):
    plate: str
    model: str
    company_id: int

class Driver(BaseModel):
    name: str
    company_id: int

class Expense(BaseModel):
    description: str
    amount: int
    is_fine: bool = False
    company_id: int

class InventoryItem(BaseModel):
    item_type: str
    serial_number: str
    assigned_truck: str
    cost: int
    company_id: int

# ---------------------------------------------------------
# AUTH ENDPOINTS: Register & Login (SaaS Ready)
# ---------------------------------------------------------
@app.post("/api/register")
def register_company(auth: CompanyAuth, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            # 1. Check if name is already taken by someone else
            check = connection.execute(
                text("SELECT id FROM companies WHERE company_name = :name"),
                {"name": auth.company_name}
            ).fetchone()
            
            if check:
                raise HTTPException(status_code=400, detail="Company name is already taken!")
            
            # 2. Create the new company with their secure PIN
            res = connection.execute(
                text("INSERT INTO companies (company_name, admin_pin) VALUES (:name, :pin) RETURNING id"),
                {"name": auth.company_name, "pin": auth.admin_pin}
            )
            new_id = res.fetchone()[0]
            connection.commit()
            return {"message": f"Account created for {auth.company_name}!", "company_id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/login")
def login_company(auth: CompanyAuth, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            # Strictly verify Name AND Pin match the database
            result = connection.execute(
                text("SELECT id FROM companies WHERE company_name = :name AND admin_pin = :pin"),
                {"name": auth.company_name, "pin": auth.admin_pin}
            ).fetchone()
            
            if result:
                return {"message": f"Welcome back, {auth.company_name}!", "company_id": result[0]}
            else:
                raise HTTPException(status_code=401, detail="Invalid Company Name or PIN!")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_receipt(file: UploadFile = File(...), api_key: str = Depends(get_api_key)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "url": f"/uploads/{file.filename}"}

# --- POST ENDPOINTS (Saving data with a Company Stamp) ---
@app.post("/api/trucks")
def add_truck(truck: Truck, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            connection.execute(
                text("INSERT INTO trucks (plate, model, company_id) VALUES (:plate, :model, :company_id)"),
                {"plate": truck.plate, "model": truck.model, "company_id": truck.company_id}
            )
            connection.commit()
        return {"message": "Truck saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drivers")
def add_driver(driver: Driver, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            connection.execute(
                text("INSERT INTO drivers (name, company_id) VALUES (:name, :company_id)"),
                {"name": driver.name, "company_id": driver.company_id}
            )
            connection.commit()
        return {"message": "Driver saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/expenses")
def add_expense(expense: Expense, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            connection.execute(
                text("INSERT INTO expenses (description, amount, is_fine, company_id) VALUES (:description, :amount, :is_fine, :company_id)"),
                {"description": expense.description, "amount": expense.amount, "is_fine": expense.is_fine, "company_id": expense.company_id}
            )
            connection.commit()
        return {"message": "Expense saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inventory")
def add_inventory(item: InventoryItem, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            connection.execute(
                text("INSERT INTO inventory (item_type, serial_number, assigned_truck, cost, company_id) VALUES (:item_type, :serial_number, :assigned_truck, :cost, :company_id)"),
                {"item_type": item.item_type, "serial_number": item.serial_number, "assigned_truck": item.assigned_truck, "cost": item.cost, "company_id": item.company_id}
            )
            connection.commit()
        return {"message": "Inventory saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- GET ENDPOINTS (Reading only your company's data) ---
@app.get("/api/trucks")
def get_trucks(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT id, plate, model FROM trucks WHERE company_id = :company_id ORDER BY id DESC"),
                {"company_id": company_id}
            )
            return [dict(row._mapping) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drivers")
def get_drivers(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT id, name FROM drivers WHERE company_id = :company_id ORDER BY id DESC"),
                {"company_id": company_id}
            )
            return [dict(row._mapping) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/expenses")
def get_expenses(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT id, description, amount, is_fine FROM expenses WHERE company_id = :company_id ORDER BY id DESC"),
                {"company_id": company_id}
            )
            return [dict(row._mapping) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/inventory")
def get_inventory(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT id, item_type, serial_number, assigned_truck, cost FROM inventory WHERE company_id = :company_id ORDER BY id DESC"),
                {"company_id": company_id}
            )
            return [dict(row._mapping) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve Uploads & Frontend
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="public")
