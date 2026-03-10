from fastapi import FastAPI, Depends, HTTPException, Security, status, File, UploadFile
from fastapi.security.api_key import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse 
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os
import shutil
from typing import Optional
import math

app = FastAPI()

# ---------------------------------------------------------
# DATABASE SETUP
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- THE DIRECTORY SETUP ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
UPLOAD_DIR = os.path.join(PUBLIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------
# SECURITY
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
class CompanyAuth(BaseModel):
    company_name: str
    admin_pin: str

class PinUpdate(BaseModel):
    company_id: int
    current_pin: str
    new_pin: str

class Truck(BaseModel):
    plate: str
    model: str
    company_id: int

class Driver(BaseModel):
    name: str
    company_id: int

class Expense(BaseModel):
    description: str
    amount: float
    is_fine: bool = False
    company_id: int

class InventoryItem(BaseModel):
    item_type: str
    serial_number: str
    assigned_truck: str
    cost: float
    company_id: int

class Trip(BaseModel):
    company_id: int
    date: str
    truck: str
    driver: str
    customer: str
    trip_type: Optional[str] = "Single"
    load_status: Optional[str] = "Loaded"
    route_from: Optional[str] = None
    route_to: Optional[str] = None
    route_full: Optional[str] = None
    distance: Optional[float] = 0.0
    cargo: Optional[str] = "-"
    total_price: Optional[float] = 0.0
    paid_amount: Optional[float] = 0.0
    balance: Optional[float] = 0.0
    trip_status: Optional[str] = "In Transit"

class Debt(BaseModel):
    company_id: int
    date: str
    customer: str
    amount: float
    description: Optional[str] = ""
    payment_method: Optional[str] = "Cash"
    bank_name: Optional[str] = ""

class Compliance(BaseModel):
    company_id: int
    record_type: str
    truck: str
    expiry_date: str
    amount: Optional[float] = 0.0
    reference_no: Optional[str] = ""
    status: Optional[str] = "Pending"

class OilPredictionRequest(BaseModel):
    truck_model: str
    current_odo: float
    last_service_odo: float
    load_status: str
    base_interval: float = 5000.0

# ---------------------------------------------------------
# AI SMART OIL CHANGE PREDICTOR (NEW)
# ---------------------------------------------------------
@app.post("/api/ai/predict-oil")
def predict_oil_health(data: OilPredictionRequest, api_key: str = Depends(get_api_key)):
    """
    AI Logic: Adjusts the safe oil lifespan based on truck type and current stress (load).
    Scania engines can handle stress slightly better than Fuso. Heavy loads degrade oil 15-25% faster.
    """
    km_driven = data.current_odo - data.last_service_odo
    
    # Base stress multiplier
    stress_factor = 1.0 
    
    # Apply conditions
    if data.load_status == "Loaded":
        if "Scania" in data.truck_model:
            stress_factor = 1.15  # 15% faster wear
        elif "Fuso" in data.truck_model:
            stress_factor = 1.25  # 25% faster wear
        else:
            stress_factor = 1.20
            
    # Calculate True Remaining KM using AI stress math
    effective_interval = data.base_interval / stress_factor
    km_remaining = effective_interval - km_driven
    
    health_percent = max(0, min(100, (km_remaining / effective_interval) * 100))
    
    status = "Good"
    color = "#10b981" # Green
    
    if health_percent <= 20:
        status = "Critical (Change Now)"
        color = "#ef4444" # Red
    elif health_percent <= 40:
        status = "Degrading (Plan Service)"
        color = "#f59e0b" # Orange

    return {
        "truck_model": data.truck_model,
        "ai_effective_interval": round(effective_interval),
        "km_driven": round(km_driven),
        "estimated_km_remaining": max(0, round(km_remaining)),
        "oil_health_percent": round(health_percent, 1),
        "status_label": status,
        "indicator_color": color
    }


# ---------------------------------------------------------
# AUTH ENDPOINTS
# ---------------------------------------------------------
@app.post("/api/register")
def register_company(auth: CompanyAuth, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("SELECT id FROM companies WHERE company_name = :name")
            if connection.execute(query, {"name": auth.company_name}).fetchone():
                raise HTTPException(status_code=400, detail="Company name is already taken!")
            
            insert_query = text("INSERT INTO companies (company_name, admin_pin) VALUES (:name, :pin) RETURNING id")
            res = connection.execute(insert_query, {"name": auth.company_name, "pin": auth.admin_pin})
            connection.commit()
            return {"message": f"Account created for {auth.company_name}!", "company_id": res.fetchone()[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/login")
def login_company(auth: CompanyAuth, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("SELECT id FROM companies WHERE company_name = :name AND admin_pin = :pin")
            result = connection.execute(query, {"name": auth.company_name, "pin": auth.admin_pin}).fetchone()
            if result:
                return {"message": f"Welcome back, {auth.company_name}!", "company_id": result[0]}
            else:
                raise HTTPException(status_code=401, detail="Invalid Company Name or PIN!")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/update-pin")
def update_pin(data: PinUpdate, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("UPDATE companies SET admin_pin = :new_pin WHERE id = :company_id AND admin_pin = :current_pin RETURNING id")
            params = {
                "new_pin": data.new_pin, 
                "company_id": data.company_id, 
                "current_pin": data.current_pin
            }
            result = connection.execute(query, params).fetchone()
            
            if result:
                connection.commit()
                return {"message": "PIN updated securely in the cloud!"}
            else:
                raise HTTPException(status_code=401, detail="Incorrect Current PIN!")
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

# ---------------------------------------------------------
# POST ENDPOINTS
# ---------------------------------------------------------
@app.post("/api/trucks")
def add_truck(truck: Truck, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("INSERT INTO trucks (plate, model, company_id) VALUES (:plate, :model, :company_id)")
            connection.execute(query, truck.dict())
            connection.commit()
        return {"message": "Truck saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drivers")
def add_driver(driver: Driver, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("INSERT INTO drivers (name, company_id) VALUES (:name, :company_id)")
            connection.execute(query, driver.dict())
            connection.commit()
        return {"message": "Driver saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/expenses")
def add_expense(expense: Expense, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("INSERT INTO expenses (description, amount, is_fine, company_id) VALUES (:description, :amount, :is_fine, :company_id)")
            connection.execute(query, expense.dict())
            connection.commit()
        return {"message": "Expense saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inventory")
def add_inventory(item: InventoryItem, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("INSERT INTO inventory (item_type, serial_number, assigned_truck, cost, company_id) VALUES (:item_type, :serial_number, :assigned_truck, :cost, :company_id)")
            connection.execute(query, item.dict())
            connection.commit()
        return {"message": "Inventory saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trips")
def add_trip(trip: Trip, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("""
                INSERT INTO trips 
                (company_id, date, truck, driver, customer, trip_type, load_status, route_from, route_to, route_full, distance, cargo, total_price, paid_amount, balance, trip_status) 
                VALUES 
                (:company_id, :date, :truck, :driver, :customer, :trip_type, :load_status, :route_from, :route_to, :route_full, :distance, :cargo, :total_price, :paid_amount, :balance, :trip_status)
            """)
            connection.execute(query, trip.dict())
            connection.commit()
        return {"message": "Trip saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/debts")
def add_debt(debt: Debt, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("""
                INSERT INTO debts 
                (company_id, date, customer, amount, description, payment_method, bank_name) 
                VALUES 
                (:company_id, :date, :customer, :amount, :description, :payment_method, :bank_name)
            """)
            connection.execute(query, debt.dict())
            connection.commit()
        return {"message": "Debt saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compliance")
def add_compliance(comp: Compliance, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("""
                INSERT INTO compliance 
                (company_id, record_type, truck, expiry_date, amount, reference_no, status) 
                VALUES 
                (:company_id, :record_type, :truck, :expiry_date, :amount, :reference_no, :status)
            """)
            connection.execute(query, comp.dict())
            connection.commit()
        return {"message": "Compliance saved!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# GET ENDPOINTS
# ---------------------------------------------------------
@app.get("/api/trucks")
def get_trucks(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("SELECT plate, model FROM trucks WHERE company_id = :company_id ORDER BY id DESC")
            result = connection.execute(query, {"company_id": company_id})
            return [{"plate": row[0], "model": row[1]} for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drivers")
def get_drivers(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("SELECT name FROM drivers WHERE company_id = :company_id ORDER BY id DESC")
            result = connection.execute(query, {"company_id": company_id})
            return [{"name": row[0]} for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/expenses")
def get_expenses(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("SELECT id, description, amount FROM expenses WHERE company_id = :company_id ORDER BY id DESC")
            result = connection.execute(query, {"company_id": company_id})
            return [{"id": row[0], "description": row[1], "amount": row[2]} for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/inventory")
def get_inventory(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("SELECT id, item_type, serial_number, assigned_truck, cost FROM inventory WHERE company_id = :company_id ORDER BY id DESC")
            result = connection.execute(query, {"company_id": company_id})
            return [{"id": row[0], "item_type": row[1], "serial_number": row[2], "assigned_truck": row[3], "cost": row[4]} for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trips")
def get_trips(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("""
                SELECT id, date, truck, driver, customer, total_price, paid_amount, balance, trip_status, distance, route_full 
                FROM trips 
                WHERE company_id = :company_id 
                ORDER BY id DESC
            """)
            result = connection.execute(query, {"company_id": company_id})
            return [
                {
                    "id": row[0],
                    "date": row[1], 
                    "truck": row[2], 
                    "driver": row[3], 
                    "customer": row[4], 
                    "total_price": row[5], 
                    "paid_amount": row[6], 
                    "balance": row[7], 
                    "trip_status": row[8],
                    "distance": row[9],
                    "route_full": row[10]
                } for row in result
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debts")
def get_debts(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("SELECT id, customer, amount, description FROM debts WHERE company_id = :company_id ORDER BY id DESC")
            result = connection.execute(query, {"company_id": company_id})
            return [{"id": row[0], "customer": row[1], "amount": row[2], "description": row[3]} for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance")
def get_compliance(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            query = text("SELECT id, record_type, truck, expiry_date, amount, status FROM compliance WHERE company_id = :company_id ORDER BY id DESC")
            result = connection.execute(query, {"company_id": company_id})
            return [
                {
                    "id": row[0],
                    "record_type": row[1], 
                    "truck": row[2], 
                    "expiry_date": row[3], 
                    "amount": row[4], 
                    "status": row[5]
                } for row in result
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# DELETE ENDPOINTS
# ---------------------------------------------------------
@app.delete("/api/delete-record")
def delete_record(table: str, record_id: int, company_id: int, api_key: str = Depends(get_api_key)):
    allowed_tables = ["trucks", "drivers", "expenses", "inventory", "trips", "debts", "compliance"]
    if table not in allowed_tables:
        raise HTTPException(status_code=400, detail="Invalid table")
    try:
        with engine.connect() as connection:
            query = text(f"DELETE FROM {table} WHERE id = :id AND company_id = :company_id")
            connection.execute(query, {"id": record_id, "company_id": company_id})
            connection.commit()
        return {"message": "Deleted securely from cloud"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/wipe-company")
def wipe_company(company_id: int, api_key: str = Depends(get_api_key)):
    try:
        with engine.connect() as connection:
            tables = ["trips", "debts", "compliance", "expenses", "inventory", "trucks", "drivers"]
            for t in tables:
                query = text(f"DELETE FROM {t} WHERE company_id = :cid")
                connection.execute(query, {"cid": company_id})
            connection.commit()
        return {"message": "Factory Reset Complete!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

try:
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except RuntimeError:
    print(f"Warning: Static directories not found.")

@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join(PUBLIC_DIR, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content=f"<h1>Error: index.html not found!</h1>", status_code=404)
