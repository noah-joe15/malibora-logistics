from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import datetime
from typing import List, Optional

# ---------------------------------------------------------
# FASTAPI APP INITIALIZATION
# ---------------------------------------------------------
app = FastAPI(title="Malibora Logistics API")

# Allow CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# SECURITY
# ---------------------------------------------------------
API_KEY = "MALIBORA_SECRET_KEY_2026"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(status_code=403, detail="Could not validate credentials")

# ---------------------------------------------------------
# DATABASE SETUP (Supabase)
# ---------------------------------------------------------
DATABASE_URL = "postgresql://postgres.yzvjutqqujbpvalelbld:jorsavantcally15@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Dependency to get DB session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# SQLALCHEMY MODELS (Database Tables)
# ---------------------------------------------------------
class MaliboraCompany(Base):
    __tablename__ = "malibora_companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    admin_pin = Column(String, nullable=False)

class MaliboraTruck(Base):
    __tablename__ = "malibora_trucks"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, index=True)
    plate = Column(String, nullable=False)
    model = Column(String, nullable=False)

class MaliboraDriver(Base):
    __tablename__ = "malibora_drivers"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, index=True)
    name = Column(String, nullable=False)

class MaliboraExpense(Base):
    __tablename__ = "malibora_expenses"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, index=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)

class MaliboraTrip(Base):
    __tablename__ = "malibora_trips"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, index=True)
    date = Column(String, nullable=False)
    truck = Column(String, nullable=False)
    driver = Column(String, nullable=False)
    customer = Column(String, nullable=False)
    total_price = Column(Float, nullable=False)
    paid_amount = Column(Float, nullable=False)
    balance = Column(Float, nullable=False)
    distance = Column(Float, nullable=False)
    cargo = Column(String, nullable=False)
    trip_status = Column(String, nullable=False)
    route_from = Column(String, nullable=False)
    route_to = Column(String, nullable=False)
    route_full = Column(String, nullable=False)
    # New Payment Fields
    payment_method = Column(String, nullable=True)
    bank_name = Column(String, nullable=True)
    bank_account = Column(String, nullable=True)
    mobile_network = Column(String, nullable=True)
    mobile_msg = Column(String, nullable=True)

class MaliboraCompliance(Base):
    __tablename__ = "malibora_compliance"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, index=True)
    record_type = Column(String, nullable=False)
    truck = Column(String, nullable=False)
    expiry_date = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)

class MaliboraDebt(Base):
    __tablename__ = "malibora_debts"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, index=True)
    date = Column(String, nullable=False)
    customer = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------
# PYDANTIC SCHEMAS (API Input/Output)
# ---------------------------------------------------------
class CompanyCreate(BaseModel):
    company_name: str
    admin_pin: str

class TruckCreate(BaseModel):
    company_id: int
    plate: str
    model: str

class DriverCreate(BaseModel):
    company_id: int
    name: str

class ExpenseCreate(BaseModel):
    company_id: int
    description: str
    amount: float

class TripCreate(BaseModel):
    company_id: int
    date: str
    truck: str
    driver: str
    customer: str
    total_price: float
    paid_amount: float
    balance: float
    distance: float
    cargo: str
    trip_status: str
    route_from: str
    route_to: str
    route_full: str
    payment_method: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    mobile_network: Optional[str] = None
    mobile_msg: Optional[str] = None

class ComplianceCreate(BaseModel):
    company_id: int
    record_type: str
    truck: str
    expiry_date: str
    amount: float
    status: str

class DebtCreate(BaseModel):
    company_id: int
    date: str
    customer: str
    amount: float
    description: str

class AIOilRequest(BaseModel):
    truck_model: str
    current_odo: float
    last_service_odo: float
    load_status: str

# ---------------------------------------------------------
# API ENDPOINTS
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "Malibora Logistics Backend is Live."}

# --- AUTHENTICATION ---
@app.post("/api/register")
def register_company(data: CompanyCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    company = db.query(MaliboraCompany).filter(MaliboraCompany.name == data.company_name).first()
    if company:
        raise HTTPException(status_code=400, detail="Company name already exists.")
    
    new_company = MaliboraCompany(name=data.company_name, admin_pin=data.admin_pin)
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return {"message": "Registration successful", "company_id": new_company.id}

@app.post("/api/login")
def login_company(data: CompanyCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    company = db.query(MaliboraCompany).filter(MaliboraCompany.name == data.company_name).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    
    # Simple check for demo purposes. Dispatchers log in by passing their truck plate as the PIN.
    # We will verify the truck plate on the frontend after getting the company ID.
    if data.admin_pin != company.admin_pin and len(data.admin_pin) < 5: 
        raise HTTPException(status_code=401, detail="Invalid Admin PIN.")
        
    return {"message": "Login successful", "company_id": company.id}

# --- TRUCKS ---
@app.get("/api/trucks")
def get_trucks(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    trucks = db.query(MaliboraTruck).filter(MaliboraTruck.company_id == company_id).all()
    return trucks

@app.post("/api/trucks")
def add_truck(data: TruckCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    new_truck = MaliboraTruck(**data.dict())
    db.add(new_truck)
    db.commit()
    return {"message": "Truck added"}

# --- DRIVERS ---
@app.get("/api/drivers")
def get_drivers(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    drivers = db.query(MaliboraDriver).filter(MaliboraDriver.company_id == company_id).all()
    return drivers

@app.post("/api/drivers")
def add_driver(data: DriverCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    new_driver = MaliboraDriver(**data.dict())
    db.add(new_driver)
    db.commit()
    return {"message": "Driver added"}

# --- EXPENSES ---
@app.get("/api/expenses")
def get_expenses(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    expenses = db.query(MaliboraExpense).filter(MaliboraExpense.company_id == company_id).order_by(MaliboraExpense.id.desc()).all()
    return expenses

@app.post("/api/expenses")
def add_expense(data: ExpenseCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    new_expense = MaliboraExpense(**data.dict())
    db.add(new_expense)
    db.commit()
    return {"message": "Expense logged"}

# --- TRIPS ---
@app.get("/api/trips")
def get_trips(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    trips = db.query(MaliboraTrip).filter(MaliboraTrip.company_id == company_id).order_by(MaliboraTrip.id.desc()).all()
    return trips

@app.post("/api/trips")
def add_trip(data: TripCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    new_trip = MaliboraTrip(**data.dict())
    db.add(new_trip)
    db.commit()
    return {"message": "Trip logged"}

# --- COMPLIANCE ---
@app.get("/api/compliance")
def get_compliance(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    compliance = db.query(MaliboraCompliance).filter(MaliboraCompliance.company_id == company_id).all()
    return compliance

@app.post("/api/compliance")
def add_compliance(data: ComplianceCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    new_comp = MaliboraCompliance(**data.dict())
    db.add(new_comp)
    db.commit()
    return {"message": "Compliance logged"}

# --- DEBTS ---
@app.post("/api/debts")
def add_debt_payment(data: DebtCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    new_debt = MaliboraDebt(**data.dict())
    db.add(new_debt)
    db.commit()
    return {"message": "Debt payment recorded"}

# --- DELETION & WIPE ---
@app.delete("/api/delete-record")
def delete_record(table: str, record_id: int, company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    if table == "trips":
        db.query(MaliboraTrip).filter(MaliboraTrip.id == record_id, MaliboraTrip.company_id == company_id).delete()
    elif table == "expenses":
        db.query(MaliboraExpense).filter(MaliboraExpense.id == record_id, MaliboraExpense.company_id == company_id).delete()
    elif table == "debts":
        db.query(MaliboraDebt).filter(MaliboraDebt.id == record_id, MaliboraDebt.company_id == company_id).delete()
    elif table == "compliance":
        db.query(MaliboraCompliance).filter(MaliboraCompliance.id == record_id, MaliboraCompliance.company_id == company_id).delete()
    db.commit()
    return {"message": "Record deleted"}

@app.delete("/api/wipe-company")
def wipe_company(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    db.query(MaliboraTruck).filter(MaliboraTruck.company_id == company_id).delete()
    db.query(MaliboraDriver).filter(MaliboraDriver.company_id == company_id).delete()
    db.query(MaliboraExpense).filter(MaliboraExpense.company_id == company_id).delete()
    db.query(MaliboraTrip).filter(MaliboraTrip.company_id == company_id).delete()
    db.query(MaliboraCompliance).filter(MaliboraCompliance.company_id == company_id).delete()
    db.query(MaliboraDebt).filter(MaliboraDebt.company_id == company_id).delete()
    db.commit()
    return {"message": "All data wiped for company"}

# --- AI PREDICTOR (MOCK FOR NOW) ---
@app.post("/api/ai/predict-oil")
def predict_oil(data: AIOilRequest, api_key: str = Depends(get_api_key)):
    # Very basic mock logic for the AI predictor
    distance_since_service = data.current_odo - data.last_service_odo
    service_interval = 5000 if data.truck_model == "Howo" else 10000
    
    health_percent = 100 - ((distance_since_service / service_interval) * 100)
    if data.load_status == "Loaded":
        health_percent -= 5 # Degrades faster when loaded
        
    health_percent = max(0, min(100, health_percent))
    
    color = "#10b981" # Green
    if health_percent < 30:
        color = "#ef4444" # Red
    elif health_percent < 60:
        color = "#f59e0b" # Yellow
        
    return {
        "oil_health_percent": round(health_percent, 1),
        "indicator_color": color,
        "recommendation": "Service required soon." if health_percent < 30 else "Oil health is good."
    }
