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
            result = connection.execute(text("SELECT version();"))
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
# DATA MODELS
# ---------------------------------------------------------
class Truck(BaseModel):
    plate: str
    model: str

class Driver(BaseModel):
    name: str

class Expense(BaseModel):
    description: str
    amount: int
    is_fine: bool = False

class InventoryItem(BaseModel):
    item_type: str
    serial_number: str
    assigned_truck: str
    cost: int

# ---------------------------------------------------------
# API ENDPOINTS (Now connected to Supabase!)
# ---------------------------------------------------------
@app.post("/api/upload")
async def upload_receipt(file: UploadFile = File(...), api_key: str = Depends(get_api_key)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "url": f"/uploads/{file.filename}"}

@app.post("/api/trucks")
def add_truck(truck: Truck, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            # Insert the new truck into the Supabase table
            connection.execute(
                text("INSERT INTO trucks (plate, model) VALUES (:plate, :model)"),
                {"plate": truck.plate, "model": truck.model}
            )
            connection.commit() # Save the changes
        return {"message": f"Truck {truck.plate} permanently saved to the cloud!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drivers")
def add_driver(driver: Driver, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            connection.execute(
                text("INSERT INTO drivers (name) VALUES (:name)"),
                {"name": driver.name}
            )
            connection.commit()
        return {"message": f"Driver {driver.name} permanently saved to the cloud!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/expenses")
def add_expense(expense: Expense, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            connection.execute(
                text("INSERT INTO expenses (description, amount, is_fine) VALUES (:description, :amount, :is_fine)"),
                {"description": expense.description, "amount": expense.amount, "is_fine": expense.is_fine}
            )
            connection.commit()
        return {"message": "Expense permanently recorded!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inventory")
def add_inventory(item: InventoryItem, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            connection.execute(
                text("INSERT INTO inventory (item_type, serial_number, assigned_truck, cost) VALUES (:item_type, :serial_number, :assigned_truck, :cost)"),
                {"item_type": item.item_type, "serial_number": item.serial_number, "assigned_truck": item.assigned_truck, "cost": item.cost}
            )
            connection.commit()
        return {"message": f"Inventory {item.item_type} permanently recorded!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/check-maintenance")
def check_maintenance(truck: Truck, api_key: str = Depends(get_api_key)):
    print(f"\n🚨 [AUTOMATED SMS SENT TO ADMIN]: Truck {truck.plate} has recorded a new trip and requires immediate mechanical review!\n")
    return {"alert_triggered": True}

# Serve Uploads & Frontend
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="public")