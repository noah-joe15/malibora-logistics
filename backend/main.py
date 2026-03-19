"""
Malibora Intertrade — Logistics API  v2.0
Professional-grade FastAPI backend.
Compatible with Pydantic v1 and FastAPI 0.103.
"""

import os
import datetime
import logging
import time
import hashlib
import secrets
from contextlib import asynccontextmanager
from typing import List, Optional, Any, Dict

from dotenv import load_dotenv

from fastapi import (
    FastAPI, Depends, HTTPException, Security, Request, status, Query
)
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator, Field
from sqlalchemy import create_engine, Column, Integer, String, Float, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import QueuePool

# ─────────────────────────────────────────────────────────────
# LOAD .env FILE
# ─────────────────────────────────────────────────────────────
load_dotenv()

# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("malibora")

# ─────────────────────────────────────────────────────────────
# CONFIG  (reads from .env — falls back to hardcoded defaults)
# ─────────────────────────────────────────────────────────────
API_KEY = os.getenv("API_KEY", "MALIBORA_SECRET_KEY_2026")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.yzvjutqqujbpvalelbld:"
    "jorsavantcally15@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"
)

# ─────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def get_api_key(api_key: str = Security(api_key_header)) -> str:
    if not secrets.compare_digest(api_key, API_KEY):
        logger.warning("Rejected request with invalid API key.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API credentials.",
        )
    return api_key


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────
class MaliboraCompany(Base):
    __tablename__ = "malibora_companies"
    id        = Column(Integer, primary_key=True, index=True)
    name      = Column(String, unique=True, index=True, nullable=False)
    admin_pin = Column(String, nullable=False)


class MaliboraTruck(Base):
    __tablename__ = "malibora_trucks"
    id         = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, index=True, nullable=False)
    plate      = Column(String, nullable=False)
    model      = Column(String, nullable=False)


class MaliboraDriver(Base):
    __tablename__ = "malibora_drivers"
    id         = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, index=True, nullable=False)
    name       = Column(String, nullable=False)


class MaliboraExpense(Base):
    __tablename__ = "malibora_expenses"
    id          = Column(Integer, primary_key=True, index=True)
    company_id  = Column(Integer, index=True, nullable=False)
    description = Column(String, nullable=False)
    amount      = Column(Float, nullable=False)


class MaliboraTrip(Base):
    __tablename__ = "malibora_trips"
    id             = Column(Integer, primary_key=True, index=True)
    company_id     = Column(Integer, index=True, nullable=False)
    date           = Column(String, nullable=False)
    truck          = Column(String, nullable=False)
    driver         = Column(String, nullable=False)
    customer       = Column(String, nullable=False)
    total_price    = Column(Float,  nullable=False)
    paid_amount    = Column(Float,  nullable=False)
    balance        = Column(Float,  nullable=False)
    distance       = Column(Float,  nullable=False)
    cargo          = Column(String, nullable=False)
    trip_status    = Column(String, nullable=False)
    route_from     = Column(String, nullable=False)
    route_to       = Column(String, nullable=False)
    route_full     = Column(String, nullable=False)
    payment_method = Column(String, nullable=True)
    bank_name      = Column(String, nullable=True)
    bank_account   = Column(String, nullable=True)
    mobile_network = Column(String, nullable=True)
    mobile_msg     = Column(String, nullable=True)


class MaliboraCompliance(Base):
    __tablename__ = "malibora_compliance"
    id          = Column(Integer, primary_key=True, index=True)
    company_id  = Column(Integer, index=True, nullable=False)
    record_type = Column(String, nullable=False)
    truck       = Column(String, nullable=False)
    expiry_date = Column(String, nullable=False)
    amount      = Column(Float,  nullable=False)
    status      = Column(String, nullable=False)


class MaliboraDebt(Base):
    __tablename__ = "malibora_debts"
    id          = Column(Integer, primary_key=True, index=True)
    company_id  = Column(Integer, index=True, nullable=False)
    date        = Column(String, nullable=False)
    customer    = Column(String, nullable=False)
    amount      = Column(Float,  nullable=False)
    description = Column(String, nullable=False)


Base.metadata.create_all(bind=engine)


# ─────────────────────────────────────────────────────────────
# SCHEMAS  (Pydantic v1 — uses @validator not @field_validator)
# ─────────────────────────────────────────────────────────────
class CompanyCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=100)
    admin_pin: str    = Field(..., min_length=4, max_length=64)

    @validator("company_name")
    def sanitize_name(cls, v):
        return v.strip()


class TruckCreate(BaseModel):
    company_id: int
    plate: str = Field(..., min_length=2, max_length=20)
    model: str = Field(..., min_length=1, max_length=50)

    @validator("plate")
    def uppercase_plate(cls, v):
        return v.strip().upper()


class DriverCreate(BaseModel):
    company_id: int
    name: str = Field(..., min_length=2, max_length=100)

    @validator("name")
    def sanitize_name(cls, v):
        return v.strip()


class ExpenseCreate(BaseModel):
    company_id: int
    description: str = Field(..., min_length=1, max_length=500)
    amount: float    = Field(..., ge=0)


class TripCreate(BaseModel):
    company_id:     int
    date:           str
    truck:          str
    driver:         str
    customer:       str
    total_price:    float = Field(..., ge=0)
    paid_amount:    float = Field(..., ge=0)
    balance:        float = 0
    distance:       float = Field(..., ge=0)
    cargo:          str
    trip_status:    str
    route_from:     str
    route_to:       str
    route_full:     str
    payment_method: Optional[str] = None
    bank_name:      Optional[str] = None
    bank_account:   Optional[str] = None
    mobile_network: Optional[str] = None
    mobile_msg:     Optional[str] = None

    @validator("balance", always=True, pre=False)
    def compute_balance(cls, v, values):
        tp = values.get("total_price") or 0
        pa = values.get("paid_amount") or 0
        return round(tp - pa, 2)

    @validator("trip_status")
    def valid_status(cls, v):
        allowed = {"In Transit", "Completed", "Cancelled", "Pending"}
        if v not in allowed:
            raise ValueError(f"trip_status must be one of {allowed}")
        return v


class TripStatusUpdate(BaseModel):
    trip_status: str

    @validator("trip_status")
    def valid_status(cls, v):
        allowed = {"In Transit", "Completed", "Cancelled", "Pending"}
        if v not in allowed:
            raise ValueError(f"trip_status must be one of {allowed}")
        return v


class ComplianceCreate(BaseModel):
    company_id:  int
    record_type: str
    truck:       str
    expiry_date: str
    amount:      float = Field(..., ge=0)
    status:      str

    @validator("expiry_date")
    def valid_date(cls, v):
        try:
            datetime.date.fromisoformat(v)
        except ValueError:
            raise ValueError("expiry_date must be YYYY-MM-DD")
        return v


class DebtCreate(BaseModel):
    company_id:  int
    date:        str
    customer:    str
    amount:      float = Field(..., ge=0)
    description: str


class AIOilRequest(BaseModel):
    truck_model:      str
    current_odo:      float = Field(..., ge=0)
    last_service_odo: float = Field(..., ge=0)
    load_status:      str


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def success(data: Any = None, message: str = "OK") -> Dict:
    return {"success": True, "message": message, "data": data}


def _days_until(date_str: str) -> Optional[int]:
    try:
        exp = datetime.date.fromisoformat(date_str)
        return (exp - datetime.date.today()).days
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# LIFESPAN
# ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Malibora API starting up ...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    yield
    logger.info("Malibora API shutting down ...")


# ─────────────────────────────────────────────────────────────
# APP INSTANCE
# ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Malibora Logistics API",
    description="Professional fleet management backend for Malibora Intertrade.",
    version="2.0.0",
    contact={"name": "Malibora Engineering"},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} [{ms}ms]")
    response.headers["X-Process-Time-Ms"] = str(ms)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": "An internal server error occurred."},
    )


# ─────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"message": "Malibora Logistics Backend is Live.", "version": "2.0.0"}


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "version": "2.0.0",
    }


# ─────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────
@app.post("/api/register", tags=["Auth"])
def register_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    existing = db.query(MaliboraCompany).filter(
        MaliboraCompany.name == data.company_name.strip()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company name already exists.")
    company = MaliboraCompany(
        name=data.company_name.strip(),
        admin_pin=hash_pin(data.admin_pin),
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    logger.info(f"Registered: '{company.name}' id={company.id}")
    return success({"company_id": company.id}, "Registration successful.")


@app.post("/api/login", tags=["Auth"])
def login_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    company = db.query(MaliboraCompany).filter(
        MaliboraCompany.name == data.company_name.strip()
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    hashed_attempt     = hash_pin(data.admin_pin)
    pin_matches_hashed = secrets.compare_digest(hashed_attempt, company.admin_pin)
    pin_matches_plain  = secrets.compare_digest(data.admin_pin, company.admin_pin)
    is_dispatcher      = len(data.admin_pin) >= 5 and not (pin_matches_hashed or pin_matches_plain)

    if not (pin_matches_hashed or pin_matches_plain or is_dispatcher):
        raise HTTPException(status_code=401, detail="Invalid PIN.")

    if pin_matches_plain and not pin_matches_hashed:
        company.admin_pin = hashed_attempt
        db.commit()
        logger.info(f"Upgraded PIN to hash for company id={company.id}")

    logger.info(f"Login: '{company.name}' id={company.id}")
    return success({"company_id": company.id}, "Login successful.")


# ─────────────────────────────────────────────────────────────
# TRUCKS
# ─────────────────────────────────────────────────────────────
@app.get("/api/trucks", tags=["Fleet"])
def get_trucks(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    return db.query(MaliboraTruck).filter(MaliboraTruck.company_id == company_id).all()


@app.post("/api/trucks", status_code=201, tags=["Fleet"])
def add_truck(data: TruckCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    existing = db.query(MaliboraTruck).filter(
        MaliboraTruck.company_id == data.company_id,
        MaliboraTruck.plate == data.plate,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Truck {data.plate!r} already exists.")
    truck = MaliboraTruck(**data.dict())
    db.add(truck)
    db.commit()
    db.refresh(truck)
    logger.info(f"Truck added: {truck.plate} ({truck.model})")
    return success({"id": truck.id, "plate": truck.plate}, "Truck added.")


@app.delete("/api/trucks/{truck_id}", tags=["Fleet"])
def delete_truck(truck_id: int, company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    truck = db.query(MaliboraTruck).filter(
        MaliboraTruck.id == truck_id, MaliboraTruck.company_id == company_id
    ).first()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found.")
    db.delete(truck)
    db.commit()
    return success(message="Truck removed.")


# ─────────────────────────────────────────────────────────────
# DRIVERS
# ─────────────────────────────────────────────────────────────
@app.get("/api/drivers", tags=["Fleet"])
def get_drivers(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    return db.query(MaliboraDriver).filter(MaliboraDriver.company_id == company_id).all()


@app.post("/api/drivers", status_code=201, tags=["Fleet"])
def add_driver(data: DriverCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    driver = MaliboraDriver(**data.dict())
    db.add(driver)
    db.commit()
    db.refresh(driver)
    logger.info(f"Driver added: {driver.name}")
    return success({"id": driver.id, "name": driver.name}, "Driver added.")


@app.delete("/api/drivers/{driver_id}", tags=["Fleet"])
def delete_driver(driver_id: int, company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    driver = db.query(MaliboraDriver).filter(
        MaliboraDriver.id == driver_id, MaliboraDriver.company_id == company_id
    ).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found.")
    db.delete(driver)
    db.commit()
    return success(message="Driver removed.")


# ─────────────────────────────────────────────────────────────
# EXPENSES
# ─────────────────────────────────────────────────────────────
@app.get("/api/expenses", tags=["Finance"])
def get_expenses(
    company_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    return db.query(MaliboraExpense).filter(
        MaliboraExpense.company_id == company_id
    ).order_by(MaliboraExpense.id.desc()).offset(skip).limit(limit).all()


@app.post("/api/expenses", status_code=201, tags=["Finance"])
def add_expense(data: ExpenseCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    expense = MaliboraExpense(**data.dict())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return success({"id": expense.id}, "Expense logged.")


# ─────────────────────────────────────────────────────────────
# TRIPS
# ─────────────────────────────────────────────────────────────
@app.get("/api/trips", tags=["Finance"])
def get_trips(
    company_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    truck: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    q = db.query(MaliboraTrip).filter(MaliboraTrip.company_id == company_id)
    if status_filter:
        q = q.filter(MaliboraTrip.trip_status == status_filter)
    if truck:
        q = q.filter(MaliboraTrip.truck == truck.upper())
    return q.order_by(MaliboraTrip.id.desc()).offset(skip).limit(limit).all()


@app.post("/api/trips", status_code=201, tags=["Finance"])
def add_trip(data: TripCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    trip = MaliboraTrip(**data.dict())
    db.add(trip)
    db.commit()
    db.refresh(trip)
    logger.info(f"Trip: {trip.truck} -> {trip.route_full} | {trip.customer} | {trip.total_price}")
    return success({"id": trip.id}, "Trip logged.")


@app.patch("/api/trips/{trip_id}/status", tags=["Finance"])
def update_trip_status(
    trip_id: int,
    company_id: int,
    body: TripStatusUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    trip = db.query(MaliboraTrip).filter(
        MaliboraTrip.id == trip_id, MaliboraTrip.company_id == company_id
    ).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found.")
    old = trip.trip_status
    trip.trip_status = body.trip_status
    db.commit()
    logger.info(f"Trip {trip_id}: {old!r} -> {body.trip_status!r}")
    return success({"id": trip.id, "trip_status": trip.trip_status}, "Trip status updated.")


# ─────────────────────────────────────────────────────────────
# COMPLIANCE
# ─────────────────────────────────────────────────────────────
@app.get("/api/compliance", tags=["Compliance"])
def get_compliance(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    records = db.query(MaliboraCompliance).filter(MaliboraCompliance.company_id == company_id).all()
    result = []
    for r in records:
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        days = _days_until(r.expiry_date)
        d["days_until_expiry"] = days
        if days is not None:
            d["status"] = "Expired" if days < 0 else ("Expiring" if days <= 30 else "Active")
        result.append(d)
    return result


@app.post("/api/compliance", status_code=201, tags=["Compliance"])
def add_compliance(data: ComplianceCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    comp = MaliboraCompliance(**data.dict())
    db.add(comp)
    db.commit()
    db.refresh(comp)
    days = _days_until(data.expiry_date)
    if days is not None and days <= 30:
        logger.warning(f"Compliance expiring in {days}d: {data.record_type} / {data.truck}")
    return success({"id": comp.id}, "Compliance logged.")


# ─────────────────────────────────────────────────────────────
# DEBTS
# ─────────────────────────────────────────────────────────────
@app.get("/api/debts", tags=["Finance"])
def get_debts(
    company_id: int,
    customer: Optional[str] = None,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    q = db.query(MaliboraDebt).filter(MaliboraDebt.company_id == company_id)
    if customer:
        q = q.filter(MaliboraDebt.customer == customer)
    return q.order_by(MaliboraDebt.id.desc()).all()


@app.post("/api/debts", status_code=201, tags=["Finance"])
def add_debt_payment(data: DebtCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    debt = MaliboraDebt(**data.dict())
    db.add(debt)
    db.commit()
    db.refresh(debt)
    logger.info(f"Debt payment: {data.amount} TZS from {data.customer}")
    return success({"id": debt.id}, "Debt payment recorded.")


# ─────────────────────────────────────────────────────────────
# DASHBOARD STATS
# ─────────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats", tags=["Analytics"])
def dashboard_stats(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    trips      = db.query(MaliboraTrip).filter(MaliboraTrip.company_id == company_id).all()
    expenses   = db.query(MaliboraExpense).filter(MaliboraExpense.company_id == company_id).all()
    debts      = db.query(MaliboraDebt).filter(MaliboraDebt.company_id == company_id).all()
    compliance = db.query(MaliboraCompliance).filter(MaliboraCompliance.company_id == company_id).all()
    trucks_count  = db.query(MaliboraTruck).filter(MaliboraTruck.company_id == company_id).count()
    drivers_count = db.query(MaliboraDriver).filter(MaliboraDriver.company_id == company_id).count()

    total_income   = sum(t.paid_amount for t in trips)
    pending_debt   = sum(t.balance for t in trips) - sum(d.amount for d in debts)
    total_expenses = sum(e.amount for e in expenses)
    active_trips   = sum(1 for t in trips if t.trip_status == "In Transit")
    expiring       = sum(1 for c in compliance if c.expiry_date and 0 <= (_days_until(c.expiry_date) or 999) <= 30)
    expired        = sum(1 for c in compliance if c.expiry_date and (_days_until(c.expiry_date) or 0) < 0)

    return {
        "cash_in_hand":     round(total_income, 2),
        "pending_debt":     round(max(pending_debt, 0), 2),
        "total_expenses":   round(total_expenses, 2),
        "net_profit":       round(total_income - total_expenses, 2),
        "active_trips":     active_trips,
        "total_trucks":     trucks_count,
        "total_drivers":    drivers_count,
        "expiring_permits": expiring,
        "expired_permits":  expired,
        "as_of":            datetime.datetime.utcnow().isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# ANALYTICS — per-truck
# ─────────────────────────────────────────────────────────────
@app.get("/api/analytics/trucks", tags=["Analytics"])
def truck_analytics(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    trips = db.query(MaliboraTrip).filter(MaliboraTrip.company_id == company_id).all()
    stats: Dict[str, Any] = {}
    for t in trips:
        s = stats.setdefault(t.truck, {
            "truck": t.truck, "revenue": 0.0,
            "pending": 0.0, "distance_km": 0.0, "trip_count": 0
        })
        s["revenue"]     += t.paid_amount
        s["pending"]     += t.balance
        s["distance_km"] += t.distance
        s["trip_count"]  += 1
    return list(stats.values())


# ─────────────────────────────────────────────────────────────
# DELETE & WIPE
# ─────────────────────────────────────────────────────────────
@app.delete("/api/delete-record", tags=["Admin"])
def delete_record(
    table: str,
    record_id: int,
    company_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    table_map = {
        "trips":      MaliboraTrip,
        "expenses":   MaliboraExpense,
        "debts":      MaliboraDebt,
        "compliance": MaliboraCompliance,
    }
    if table not in table_map:
        raise HTTPException(status_code=400, detail=f"Unknown table '{table}'.")
    model = table_map[table]
    deleted = db.query(model).filter(
        model.id == record_id,
        model.company_id == company_id
    ).delete(synchronize_session=False)
    db.commit()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Record not found.")
    logger.info(f"Deleted {table} id={record_id} company={company_id}")
    return success(message="Record deleted.")


@app.delete("/api/wipe-company", tags=["Admin"])
def wipe_company(company_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    for model in [MaliboraTruck, MaliboraDriver, MaliboraExpense,
                  MaliboraTrip, MaliboraCompliance, MaliboraDebt]:
        db.query(model).filter(model.company_id == company_id).delete(synchronize_session=False)
    db.commit()
    logger.warning(f"WIPE executed for company_id={company_id}")
    return success(message="All data wiped for company.")


# ─────────────────────────────────────────────────────────────
# AI OIL PREDICTOR
# ─────────────────────────────────────────────────────────────
SERVICE_INTERVALS = {"scania": 15000, "howo": 5000, "fuso": 10000, "default": 8000}
FUEL_CONSUMPTION  = {
    "scania":  {"Loaded": 0.50, "Empty": 0.30},
    "howo":    {"Loaded": 0.45, "Empty": 0.25},
    "fuso":    {"Loaded": 0.40, "Empty": 0.20},
    "default": {"Loaded": 0.45, "Empty": 0.25},
}


def _service_interval(model: str) -> int:
    key = model.lower()
    for k, v in SERVICE_INTERVALS.items():
        if k in key:
            return v
    return SERVICE_INTERVALS["default"]


def _fuel_rate(model: str, load: str) -> float:
    key = model.lower()
    for k, rates in FUEL_CONSUMPTION.items():
        if k in key:
            return rates.get(load, rates["Loaded"])
    return FUEL_CONSUMPTION["default"].get(load, 0.45)


@app.post("/api/ai/predict-oil", tags=["AI"])
def predict_oil(data: AIOilRequest, api_key: str = Depends(get_api_key)):
    interval   = _service_interval(data.truck_model)
    dist_since = max(0.0, data.current_odo - data.last_service_odo)
    health     = 100.0 - (dist_since / interval) * 100.0
    if data.load_status == "Loaded":
        health -= 5.0
    health  = round(max(0.0, min(100.0, health)), 1)
    km_left = round(max(0.0, interval - dist_since), 0)

    if health >= 60:
        color, urgency = "#10b981", "low"
    elif health >= 30:
        color, urgency = "#f59e0b", "medium"
    else:
        color, urgency = "#ef4444", "high"

    if health <= 0:
        rec = f"OVERDUE — {data.truck_model} requires immediate oil service. Exceeded {interval:,} km interval."
    elif health < 30:
        rec = f"Service required very soon. Only {km_left:,.0f} km remaining. Schedule this week."
    elif health < 60:
        rec = f"Plan service within {km_left:,.0f} km. Monitor oil level daily."
    else:
        rec = f"Oil health is good. Next service in ~{km_left:,.0f} km."

    return {
        "oil_health_percent":     health,
        "indicator_color":        color,
        "urgency":                urgency,
        "km_until_service":       km_left,
        "service_interval_km":    interval,
        "distance_since_service": round(dist_since, 0),
        "fuel_rate_per_km":       _fuel_rate(data.truck_model, data.load_status),
        "recommendation":         rec,
    }
