"""
FraudShieldAI Pay - FastAPI Backend
Main application entry point for the synthetic payment ecosystem.

Run: uvicorn backend.app:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from fastapi import Body, FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, desc, func, text
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import json
import random
import uuid
from datetime import datetime

# Import database and models
from backend.database import get_db, SessionLocal, engine
from backend.fraud_service import fraud_service
from backend.models.models import Base
from backend.models.models import (
    Account,
    AccountType,
    Alert,
    Device,
    DeviceStatus,
    Merchant,
    PaymentRequest,
    Reward,
    RiskLevel,
    Transaction,
    TransactionStatus,
    User,
    UserStatus,
)

# Import routers (will be created in phases)
# from backend.routers import auth, payments, users, accounts, devices, transactions, analyst, fraud

# Initialize database on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and cleanup on shutdown."""
    # Startup
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_data(db)
    finally:
        db.close()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="FraudShieldAI Pay",
    description="Synthetic payment ecosystem with integrated fraud detection",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================


@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "FraudShieldAI Pay",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/info", tags=["System"])
async def info():
    """Get service information."""
    return {
        "name": "FraudShieldAI Pay",
        "tagline": "Pay. Connect. Stay Protected.",
        "environment": "Synthetic Payment Simulation",
        "mode": "SIMULATION",
        "disclaimer": "This application is a closed synthetic payment simulation. It does not connect to real UPI, banking systems, payment processors, or real money.",
    }


# ============================================================================
# AUTH, PROFILE & PAYMENT ENDPOINTS
# ============================================================================


@app.get("/api/demo-profiles", tags=["Auth"])
async def demo_profiles(db: Session = Depends(get_db)):
    """List predefined dataset profiles and their demo credentials."""
    ensure_demo_data(db)
    users = db.query(User).order_by(User.user_id).all()
    credentials = {profile["user_id"]: profile for profile in DEMO_PROFILES}
    return {
        "profiles": [
            {
                **public_user(user),
                "password": credentials.get(user.user_id, {}).get("password", "pass001"),
                "pin": credentials.get(user.user_id, {}).get("pin", "1234"),
            }
            for user in users
            if user.user_id in credentials
        ]
    }


@app.post("/api/auth/login", tags=["Auth"])
async def login(req: dict = Body(...), db: Session = Depends(get_db)):
    """Login with a predefined profile credential."""
    req = LoginRequest.model_validate(req)
    ensure_demo_data(db)
    user = find_user(db, req.identifier)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown profile")

    expected = PROFILE_BY_ID.get(user.user_id, {}).get("password")
    if expected is None or req.password != expected:
        raise HTTPException(status_code=401, detail="Invalid password")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Profile is not active")

    if req.device_id:
        safe_device_id = scoped_device_id(user, req.device_id)
        device = db.query(Device).filter(Device.user_id == user.id, Device.device_id == safe_device_id).first()
        if device is None:
            db.add(
                Device(
                    device_id=safe_device_id,
                    user_id=user.id,
                    device_name=req.device_name or "Browser device",
                    device_type="Web",
                    browser="Browser",
                    os="Web",
                    location=PROFILE_BY_ID.get(user.user_id, {}).get("location"),
                    trusted=False,
                    status=DeviceStatus.NEW,
                )
            )
            db.add(
                Alert(
                    user_id=user.id,
                    alert_type="NEW_DEVICE",
                    severity="WARNING",
                    message="New device login detected.",
                    details={"device_id": safe_device_id},
                )
            )
            db.commit()

    token = uuid.uuid4().hex
    TOKEN_TO_USER[token] = user.user_id
    return {"token": token, "user": public_user(user)}


@app.get("/api/auth/me", tags=["Auth"])
async def me(token: str, db: Session = Depends(get_db)):
    """Get the currently logged-in profile for a session token."""
    return {"user": public_user(get_user_from_token(db, token))}


@app.get("/api/users", tags=["Users"])
async def list_users(db: Session = Depends(get_db)):
    """List payment profiles available for transfers."""
    ensure_demo_data(db)
    return {
        "users": [
            public_user(user)
            for user in db.query(User).order_by(User.name).all()
            if user.user_id in PROFILE_BY_ID
        ]
    }


@app.get("/api/wallet", tags=["Wallet"])
async def wallet(token: str, db: Session = Depends(get_db)):
    """Get wallet summary."""
    user = get_user_from_token(db, token)
    return {"wallet": public_user(user)}


@app.post("/api/payments/send", tags=["Payments"])
async def send_money(req: dict = Body(...), db: Session = Depends(get_db)):
    """Send FraudShield Money between predefined profiles."""
    req = SendMoneyRequest.model_validate(req)
    sender = get_user_from_token(db, req.token)
    receiver = find_user(db, req.receiver)
    if receiver is None:
        raise HTTPException(status_code=404, detail="Receiver not found")
    tx = process_transfer(
        db,
        sender=sender,
        receiver=receiver,
        amount=req.amount,
        pin=req.pin,
        note=req.note,
        device_id=req.device_id,
        location=req.location,
    )
    db.commit()
    db.refresh(tx)
    payload = {"type": "transaction", "transaction": serialize_transaction(tx)}
    await manager.broadcast(payload)
    return {"transaction": serialize_transaction(tx), "sender": public_user(sender), "receiver": public_user(receiver)}


@app.post("/api/qr/pay", tags=["Payments"])
async def qr_pay(req: dict = Body(...), db: Session = Depends(get_db)):
    """Pay by a profile or merchant QR payload."""
    req = SendMoneyRequest.model_validate(req)
    receiver_key = req.receiver.replace("FSQR:", "").strip()
    sender = get_user_from_token(db, req.token)
    merchant = db.query(Merchant).filter(Merchant.merchant_id == receiver_key).first()
    if merchant is not None:
        if merchant.status != "ACTIVE" or merchant.account_id is None:
            raise HTTPException(status_code=409, detail="Merchant is not active")
        merchant_account = db.query(Account).filter(Account.id == merchant.account_id).first()
        receiver = db.query(User).filter(User.id == merchant_account.user_id).first() if merchant_account else None
    else:
        receiver = find_user(db, receiver_key)
    if receiver is None:
        raise HTTPException(status_code=404, detail="QR receiver not found")
    tx = process_transfer(
        db,
        sender=sender,
        receiver=receiver,
        amount=req.amount,
        pin=req.pin,
        note=req.note or "QR payment",
        device_id=req.device_id,
        location=req.location,
        merchant_id=merchant.id if merchant else None,
    )
    db.commit()
    db.refresh(tx)
    await manager.broadcast({"type": "transaction", "transaction": serialize_transaction(tx)})
    return {"transaction": serialize_transaction(tx), "sender": public_user(sender), "receiver": public_user(receiver)}


@app.post("/api/requests", tags=["Requests"])
async def create_request(req: dict = Body(...), db: Session = Depends(get_db)):
    """Request FraudShield Money from another profile."""
    req = CreatePaymentRequest.model_validate(req)
    requester = get_user_from_token(db, req.token)
    payer = find_user(db, req.payer)
    if payer is None:
        raise HTTPException(status_code=404, detail="Payer not found")
    if requester.id == payer.id:
        raise HTTPException(status_code=400, detail="Cannot request money from your own profile")

    row = PaymentRequest(
        request_id=f"REQ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}",
        requester_user_id=requester.id,
        payer_user_id=payer.id,
        amount=round(float(req.amount), 2),
        currency="FSM",
        note=req.note,
        status="PENDING",
    )
    db.add(row)
    db.add(
        Alert(
            user_id=payer.id,
            alert_type="PAYMENT_REQUEST",
            severity="INFO",
            message=f"{requester.name} requested {row.amount} FSM.",
            details={"request_id": row.request_id},
        )
    )
    db.commit()
    return {"request": serialize_request(row)}


@app.get("/api/requests", tags=["Requests"])
async def list_requests(token: str, db: Session = Depends(get_db)):
    """List sent and received collect requests for the current profile."""
    user = get_user_from_token(db, token)
    rows = (
        db.query(PaymentRequest)
        .filter(or_(PaymentRequest.requester_user_id == user.id, PaymentRequest.payer_user_id == user.id))
        .order_by(desc(PaymentRequest.created_at))
        .limit(100)
        .all()
    )
    return {"requests": [serialize_request(row, current_user=user) for row in rows]}


@app.post("/api/requests/{request_id}/approve", tags=["Requests"])
async def approve_request(request_id: str, req: dict = Body(...), db: Session = Depends(get_db)):
    """Approve a collect request and move money from payer to requester."""
    req = RequestDecisionBody.model_validate(req)
    payer = get_user_from_token(db, req.token)
    row = db.query(PaymentRequest).filter(PaymentRequest.request_id == request_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Payment request not found")
    if row.payer_user_id != payer.id:
        raise HTTPException(status_code=403, detail="Only the payer can approve this request")
    if row.status != "PENDING":
        raise HTTPException(status_code=409, detail="Request is no longer pending")
    if not req.pin:
        raise HTTPException(status_code=400, detail="Payment PIN is required")

    requester = db.query(User).filter(User.id == row.requester_user_id).first()
    tx = process_transfer(
        db,
        sender=payer,
        receiver=requester,
        amount=row.amount,
        pin=req.pin,
        note=row.note or f"Approved request {row.request_id}",
        device_id=req.device_id,
    )
    row.status = "APPROVED" if tx.status != TransactionStatus.BLOCKED else "BLOCKED"
    row.transaction_id = tx.transaction_id
    db.commit()
    db.refresh(row)
    db.refresh(tx)
    await manager.broadcast({"type": "transaction", "transaction": serialize_transaction(tx)})
    return {"request": serialize_request(row, current_user=payer), "transaction": serialize_transaction(tx)}


@app.post("/api/requests/{request_id}/reject", tags=["Requests"])
async def reject_request(request_id: str, req: dict = Body(...), db: Session = Depends(get_db)):
    """Reject a collect request."""
    req = RequestDecisionBody.model_validate(req)
    payer = get_user_from_token(db, req.token)
    row = db.query(PaymentRequest).filter(PaymentRequest.request_id == request_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Payment request not found")
    if row.payer_user_id != payer.id:
        raise HTTPException(status_code=403, detail="Only the payer can reject this request")
    row.status = "REJECTED"
    db.commit()
    return {"request": serialize_request(row, current_user=payer)}


@app.get("/api/transactions", tags=["Transactions"])
async def transactions(token: str | None = None, db: Session = Depends(get_db)):
    """List transactions for a user or all transactions when token is omitted."""
    query = db.query(Transaction).order_by(desc(Transaction.timestamp))
    if token:
        user = get_user_from_token(db, token)
        query = query.filter(or_(Transaction.sender_user_id == user.id, Transaction.receiver_user_id == user.id))
    return {"transactions": [serialize_transaction(tx) for tx in query.limit(100).all()]}


@app.get("/api/transactions/{transaction_id}/receipt", tags=["Transactions"])
async def transaction_receipt(transaction_id: str, token: str, db: Session = Depends(get_db)):
    """Return a downloadable receipt for an owned transaction."""
    tx = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    user_id = TOKEN_TO_USER.get(token)
    is_owner = user_id in {
        tx.sender_user.user_id if tx.sender_user else None,
        tx.receiver_user.user_id if tx.receiver_user else None,
    }
    if token not in ADMIN_TOKENS and not is_owner:
        raise HTTPException(status_code=403, detail="Transaction owner or analyst session required")
    return {
        "receipt_type": "FraudShield Money receipt",
        "issued_at": datetime.utcnow().isoformat(),
        "transaction": serialize_transaction(tx),
    }


@app.get("/api/insights", tags=["Transactions"])
async def spending_insights(token: str, db: Session = Depends(get_db)):
    """Return recent contacts and lightweight spending summaries for a user."""
    user = get_user_from_token(db, token)
    rows = (
        db.query(Transaction)
        .filter(or_(Transaction.sender_user_id == user.id, Transaction.receiver_user_id == user.id))
        .order_by(desc(Transaction.timestamp))
        .limit(100)
        .all()
    )
    contacts: dict[str, dict] = {}
    categories: dict[str, float] = {}
    for row in rows:
        other = row.receiver_user if row.sender_user_id == user.id else row.sender_user
        if other is not None and other.user_id != user.user_id:
            entry = contacts.setdefault(other.user_id, {"user_id": other.user_id, "name": other.name, "count": 0, "last_transaction": None})
            entry["count"] += 1
            entry["last_transaction"] = row.timestamp.isoformat() if row.timestamp else None
        note = (row.description or "").lower()
        category = "Other"
        if any(word in note for word in ("food", "cafe", "restaurant", "lunch")):
            category = "Food"
        elif any(word in note for word in ("shop", "store", "grocery", "mart")):
            category = "Shopping"
        elif any(word in note for word in ("refund", "cashback")):
            category = "Refunds"
        categories[category] = categories.get(category, 0) + float(row.amount)
    return {
        "recent_contacts": sorted(contacts.values(), key=lambda item: (-item["count"], item["name"]))[:8],
        "spending_categories": [{"category": key, "amount": round(value, 2)} for key, value in sorted(categories.items(), key=lambda item: -item[1])],
        "total_volume": round(sum(float(row.amount) for row in rows if row.status != TransactionStatus.BLOCKED), 2),
    }


@app.get("/api/rewards", tags=["Rewards"])
async def rewards(token: str, db: Session = Depends(get_db)):
    """List cashback rewards earned by the current profile."""
    user = get_user_from_token(db, token)
    rows = db.query(Reward).filter(Reward.user_id == user.id).order_by(desc(Reward.created_at)).limit(50).all()
    return {
        "rewards": [
            {
                "amount": round(float(row.amount or 0), 2),
                "type": row.reward_type,
                "description": row.description,
                "transaction_id": row.transaction_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
        "total": round(sum(float(row.amount or 0) for row in rows), 2),
    }


@app.get("/api/devices", tags=["Devices"])
async def devices(token: str, db: Session = Depends(get_db)):
    """List devices registered to the current profile."""
    user = get_user_from_token(db, token)
    rows = db.query(Device).filter(Device.user_id == user.id).order_by(desc(Device.last_seen)).all()
    return {"devices": [
        {
            "device_id": row.device_id,
            "name": row.device_name,
            "type": row.device_type,
            "location": row.location,
            "trusted": bool(row.trusted),
            "status": row.status.value if hasattr(row.status, "value") else row.status,
            "last_seen": row.last_seen.isoformat() if row.last_seen else None,
        }
        for row in rows
    ]}


class DeviceTrustRequest(BaseModel):
    token: str
    trusted: bool


@app.post("/api/devices/{device_id}/trust", tags=["Devices"])
async def update_device_trust(device_id: str, req: DeviceTrustRequest, db: Session = Depends(get_db)):
    """Trust or revoke a device owned by the current profile."""
    user = get_user_from_token(db, req.token)
    row = db.query(Device).filter(Device.device_id == device_id, Device.user_id == user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")
    row.trusted = req.trusted
    row.status = DeviceStatus.TRUSTED if req.trusted else DeviceStatus.NEW
    db.commit()
    return {"device_id": row.device_id, "trusted": bool(row.trusted), "status": row.status.value}


@app.get("/api/risk-trend", tags=["Fraud"])
async def risk_trend(token: str, db: Session = Depends(get_db)):
    """Return recent transaction risk scores for the current profile."""
    user = get_user_from_token(db, token)
    rows = db.query(Transaction).filter(
        or_(Transaction.sender_user_id == user.id, Transaction.receiver_user_id == user.id)
    ).order_by(desc(Transaction.timestamp)).limit(20).all()
    trend = [
        {
            "transaction_id": row.transaction_id,
            "risk_score": round(float(row.risk_score or 0), 2),
            "risk_level": row.risk_level.value if hasattr(row.risk_level, "value") else row.risk_level,
            "created_at": row.timestamp.isoformat() if row.timestamp else None,
        }
        for row in reversed(rows)
    ]
    average = round(sum(item["risk_score"] for item in trend) / len(trend), 2) if trend else 0
    return {"average_risk": average, "trend": trend}


@app.get("/api/alerts", tags=["Fraud"])
async def alerts(token: str, db: Session = Depends(get_db)):
    """List security alerts for the current profile."""
    user = get_user_from_token(db, token)
    rows = db.query(Alert).filter(Alert.user_id == user.id).order_by(desc(Alert.created_at)).limit(50).all()
    return {
        "alerts": [
            {
                "id": alert.id,
                "type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "details": alert.details or {},
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            }
            for alert in rows
        ]
    }


@app.get("/api/merchants", tags=["Merchants"])
async def list_merchants(db: Session = Depends(get_db)):
    """List active demo merchants and their static QR payloads."""
    ensure_demo_data(db)
    return {
        "merchants": [
            {
                "merchant_id": merchant.merchant_id,
                "name": merchant.name,
                "category": merchant.category,
                "location": merchant.location,
                "qr_code": merchant.qr_code,
                "status": merchant.status,
            }
            for merchant in db.query(Merchant).filter(Merchant.status == "ACTIVE").order_by(Merchant.name).all()
        ]
    }


@app.get("/api/merchants/{merchant_id}/dashboard", tags=["Merchants"])
async def merchant_dashboard(merchant_id: str, token: str, db: Session = Depends(get_db)):
    """Return merchant sales and daily/weekly summaries."""
    merchant = db.query(Merchant).filter(Merchant.merchant_id == merchant_id).first()
    if merchant is None or merchant.account_id is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    account = db.query(Account).filter(Account.id == merchant.account_id).first()
    owner = db.query(User).filter(User.id == account.user_id).first() if account else None
    if owner is None:
        raise HTTPException(status_code=409, detail="Merchant owner is unavailable")
    if token not in ADMIN_TOKENS and TOKEN_TO_USER.get(token) != owner.user_id:
        raise HTTPException(status_code=403, detail="Merchant owner or analyst session required")
    sales = db.query(Transaction).filter(
        Transaction.merchant_id == merchant.id,
        Transaction.status.in_([TransactionStatus.COMPLETED, TransactionStatus.WARNING]),
    ).order_by(desc(Transaction.timestamp)).all()
    now = datetime.utcnow()
    daily = sum(float(tx.amount) for tx in sales if tx.timestamp and (now - tx.timestamp).days < 1)
    weekly = sum(float(tx.amount) for tx in sales if tx.timestamp and (now - tx.timestamp).days < 7)
    return {
        "merchant": {"merchant_id": merchant.merchant_id, "name": merchant.name, "qr_code": merchant.qr_code},
        "summary": {"daily_sales": round(daily, 2), "weekly_sales": round(weekly, 2), "transactions": len(sales)},
        "sales": [serialize_transaction(tx) for tx in sales[:100]],
    }


@app.post("/api/merchants/{merchant_id}/refund/{transaction_id}", tags=["Merchants"])
async def refund_merchant_payment(merchant_id: str, transaction_id: str, req: dict = Body(...), db: Session = Depends(get_db)):
    """Refund a completed merchant payment to its original sender."""
    token = str(req.get("token", ""))
    merchant = db.query(Merchant).filter(Merchant.merchant_id == merchant_id).first()
    tx = db.query(Transaction).filter(Transaction.transaction_id == transaction_id, Transaction.merchant_id == (merchant.id if merchant else None)).first()
    if merchant is None or tx is None:
        raise HTTPException(status_code=404, detail="Merchant payment not found")
    account = db.query(Account).filter(Account.id == merchant.account_id).first()
    owner = db.query(User).filter(User.id == account.user_id).first() if account else None
    if owner is None or (token not in ADMIN_TOKENS and TOKEN_TO_USER.get(token) != owner.user_id):
        raise HTTPException(status_code=403, detail="Merchant owner or analyst session required")
    if tx.status not in {TransactionStatus.COMPLETED, TransactionStatus.WARNING}:
        raise HTTPException(status_code=409, detail="Only completed payments can be refunded")
    refund = process_transfer(
        db,
        sender=owner,
        receiver=tx.sender_user,
        amount=float(tx.amount),
        pin=PAYMENT_PINS.get(owner.user_id, "1234"),
        note=f"Refund for {transaction_id}",
        merchant_id=merchant.id,
    )
    tx.status = TransactionStatus.CANCELLED
    tx.signals = {**(tx.signals or {}), "refund_transaction_id": refund.transaction_id}
    db.commit()
    db.refresh(refund)
    return {"original_transaction": serialize_transaction(tx), "refund": serialize_transaction(refund)}


ADMIN_USERNAME = "analyst"
ADMIN_PASSWORD = "admin001"
ADMIN_TOKENS: set[str] = set()


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminUserStatusBody(BaseModel):
    token: str
    status: str = Field(..., pattern="^(ACTIVE|SUSPENDED|BLOCKED)$")


def require_admin(token: str) -> None:
    if token not in ADMIN_TOKENS:
        raise HTTPException(status_code=401, detail="Valid analyst session required")


@app.post("/api/admin/login", tags=["Analyst"])
async def admin_login(req: AdminLoginRequest):
    """Create a demo analyst session for protected monitoring actions."""
    if req.username != ADMIN_USERNAME or req.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid analyst credentials")
    token = uuid.uuid4().hex
    ADMIN_TOKENS.add(token)
    return {"token": token, "role": "analyst"}


@app.get("/api/admin/dashboard", tags=["Analyst"])
async def admin_dashboard(token: str, db: Session = Depends(get_db)):
    """Analyst dashboard metrics and latest fraud feed."""
    require_admin(token)
    users = db.query(User).filter(User.user_id.in_(list(PROFILE_BY_ID))).count()
    txs = db.query(Transaction).all()
    total_volume = sum(float(tx.amount) for tx in txs if tx.status != TransactionStatus.BLOCKED)
    return {
        "metrics": {
            "users": users,
            "transactions": len(txs),
            "volume": round(total_volume, 2),
            "flagged": len([tx for tx in txs if tx.status == TransactionStatus.WARNING]),
            "blocked": len([tx for tx in txs if tx.status == TransactionStatus.BLOCKED]),
        },
        "risk_profiles": [public_user(user) for user in db.query(User).filter(User.user_id.in_(list(PROFILE_BY_ID))).all()],
        "live_feed": [serialize_transaction(tx) for tx in sorted(txs, key=lambda row: row.timestamp or datetime.min, reverse=True)[:20]],
    }


@app.post("/api/admin/users/{user_id}/status", tags=["Analyst"])
async def update_user_status(user_id: str, req: dict = Body(...), db: Session = Depends(get_db)):
    """Freeze, suspend, or reactivate a demo profile."""
    req = AdminUserStatusBody.model_validate(req)
    require_admin(req.token)
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    user.status = UserStatus(req.status)
    db.add(
        Alert(
            user_id=user.id,
            alert_type="PROFILE_STATUS",
            severity="WARNING" if req.status != "ACTIVE" else "INFO",
            message=f"Profile status changed to {req.status}.",
            details={"status": req.status},
        )
    )
    db.commit()
    return {"user": public_user(user)}


# ============================================================================
# WEBSOCKET SUPPORT (Phase L)
# ============================================================================

class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting: {e}")


manager = ConnectionManager()


# ============================================================================
# DEMO PROFILE, AUTH & FRAUD HELPERS
# ============================================================================


DEMO_PROFILES = [
    {
        "user_id": "faris",
        "name": "Faris",
        "phone": "9876543210",
        "email": "faris@fsaipay.local",
        "upi_id": "faris@fsaipay",
        "password": "pass001",
        "pin": "1234",
        "balance": 50000,
        "risk": RiskLevel.LOW,
        "location": "Mysuru, KA",
        "persona": "Regular personal account",
    },
    {
        "user_id": "rahul",
        "name": "Rahul",
        "phone": "9876543211",
        "email": "rahul@fsaipay.local",
        "upi_id": "rahul@fsaipay",
        "password": "pass002",
        "pin": "1234",
        "balance": 36000,
        "risk": RiskLevel.MEDIUM,
        "location": "Bengaluru, KA",
        "persona": "Frequent peer transfers",
    },
    {
        "user_id": "ahmed",
        "name": "Ahmed",
        "phone": "9876543212",
        "email": "ahmed@fsaipay.local",
        "upi_id": "ahmed@fsaipay",
        "password": "pass003",
        "pin": "1234",
        "balance": 42000,
        "risk": RiskLevel.LOW,
        "location": "Pune, MH",
        "persona": "Steady salary profile",
    },
    {
        "user_id": "priya",
        "name": "Priya",
        "phone": "9876543213",
        "email": "priya@fsaipay.local",
        "upi_id": "priya@fsaipay",
        "password": "pass004",
        "pin": "1234",
        "balance": 62000,
        "risk": RiskLevel.LOW,
        "location": "Mumbai, MH",
        "persona": "Premium low-risk profile",
    },
    {
        "user_id": "ananya",
        "name": "Ananya",
        "phone": "9876543214",
        "email": "ananya@fsaipay.local",
        "upi_id": "ananya@fsaipay",
        "password": "pass005",
        "pin": "1234",
        "balance": 28000,
        "risk": RiskLevel.MEDIUM,
        "location": "Delhi, DL",
        "persona": "New-device sensitive profile",
    },
    {
        "user_id": "arjun",
        "name": "Arjun",
        "phone": "9876543215",
        "email": "arjun@fsaipay.local",
        "upi_id": "arjun@fsaipay",
        "password": "pass006",
        "pin": "1234",
        "balance": 46000,
        "risk": RiskLevel.MEDIUM,
        "location": "Hyderabad, TG",
        "persona": "Travel and merchant-heavy profile",
    },
    {
        "user_id": "kiran",
        "name": "Kiran",
        "phone": "9876543216",
        "email": "kiran@fsaipay.local",
        "upi_id": "kiran@fsaipay",
        "password": "pass007",
        "pin": "1234",
        "balance": 78000,
        "risk": RiskLevel.LOW,
        "location": "Bengaluru, KA",
        "persona": "Verified merchant profile",
    },
    {
        "user_id": "neha",
        "name": "Neha",
        "phone": "9876543217",
        "email": "neha@fsaipay.local",
        "upi_id": "neha@fsaipay",
        "password": "pass008",
        "pin": "1234",
        "balance": 30000,
        "risk": RiskLevel.HIGH,
        "location": "Chennai, TN",
        "persona": "High-velocity risk profile",
    },
]

PROFILE_BY_ID = {profile["user_id"]: profile for profile in DEMO_PROFILES}
TOKEN_TO_USER: dict[str, str] = {}
PAYMENT_PINS = {profile["user_id"]: profile["pin"] for profile in DEMO_PROFILES}


class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Phone, UPI ID, email, or profile ID")
    password: str
    device_id: str | None = None
    device_name: str | None = None


class SendMoneyRequest(BaseModel):
    token: str
    receiver: str = Field(..., description="Receiver phone, UPI ID, or profile ID")
    amount: float = Field(..., gt=0)
    pin: str = Field(..., min_length=4, max_length=6)
    note: str = ""
    device_id: str | None = None
    location: str | None = None


class CreatePaymentRequest(BaseModel):
    token: str
    payer: str = Field(..., description="Who should pay this request")
    amount: float = Field(..., gt=0)
    note: str = ""


class RequestDecisionBody(BaseModel):
    token: str
    pin: str | None = None
    device_id: str | None = None


def normalize_identifier(value: str) -> str:
    return value.strip().lower().replace("+91-", "").replace("+91", "").replace(" ", "")


def clean_phone(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("+91-", "").replace("+91", "").replace(" ", "")


def scoped_device_id(user: User, device_id: str | None) -> str | None:
    if not device_id:
        return None
    return f"{user.user_id}:{device_id}"[:240]


def public_user(user: User) -> dict:
    profile = PROFILE_BY_ID.get(user.user_id, {})
    account = user.accounts[0] if user.accounts else None
    return {
        "id": user.id,
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "phone": clean_phone(user.phone),
        "upi_id": user.upi_id,
        "status": user.status.value if hasattr(user.status, "value") else user.status,
        "balance": round(float(account.balance if account else 0), 2),
        "currency": "FSM",
        "risk_level": profile.get("risk", RiskLevel.LOW).value,
        "persona": profile.get("persona", "Dataset profile"),
        "location": profile.get("location", "Unknown"),
    }


def find_user(db: Session, identifier: str) -> User | None:
    normalized = normalize_identifier(identifier)
    return (
        db.query(User)
        .filter(
            or_(
                func.lower(User.user_id) == normalized,
                func.lower(User.email) == normalized,
                func.lower(User.upi_id) == normalized,
                User.phone == normalized,
                User.phone == f"+91-{normalized}",
                User.phone == f"+91{normalized}",
            )
        )
        .first()
    )


def get_user_from_token(db: Session, token: str) -> User:
    user_id = TOKEN_TO_USER.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Session user no longer exists")
    return user


def ensure_demo_data(db: Session) -> None:
    ensure_runtime_schema()
    for profile in DEMO_PROFILES:
        user = db.query(User).filter(User.user_id == profile["user_id"]).first()
        if user is None:
            user = User(
                user_id=profile["user_id"],
                name=profile["name"],
                email=profile["email"],
                phone=profile["phone"],
                avatar=profile["name"][:1],
                password_hash=f"demo:{profile['password']}",
                upi_id=profile["upi_id"],
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            db.flush()
        else:
            user.phone = clean_phone(user.phone) or profile["phone"]
            user.password_hash = f"demo:{profile['password']}"
            user.upi_id = user.upi_id or profile["upi_id"]

        account = db.query(Account).filter(Account.user_id == user.id).first()
        if account is None:
            account = Account(
                account_id=f"FSM_{profile['user_id'].upper()}",
                user_id=user.id,
                account_type=AccountType.WALLET,
                balance=float(profile["balance"]),
                currency="FSM",
                status="ACTIVE",
            )
            db.add(account)
        else:
            account.currency = "FSM"

        device = (
            db.query(Device)
            .filter(Device.user_id == user.id, Device.device_id == f"WEB_{profile['user_id'].upper()}")
            .first()
        )
        if device is None:
            db.add(
                Device(
                    device_id=f"WEB_{profile['user_id'].upper()}",
                    user_id=user.id,
                    device_name="Demo browser",
                    device_type="Web",
                    os="Web",
                    browser="Browser",
                    location=profile["location"],
                    trusted=True,
                    status=DeviceStatus.TRUSTED,
                )
            )

    merchants = [
        ("MRC_CAFE", "Mysuru Cafe", "Food"),
        ("MRC_TECH", "Tech World", "Electronics"),
        ("MRC_MART", "SuperMart", "Grocery"),
    ]
    merchant_owner = db.query(User).filter(User.user_id == "kiran").first()
    merchant_account = db.query(Account).filter(Account.user_id == merchant_owner.id).first() if merchant_owner else None
    for merchant_id, name, category in merchants:
        merchant = db.query(Merchant).filter(Merchant.merchant_id == merchant_id).first()
        if merchant is None:
            db.add(
                Merchant(
                    merchant_id=merchant_id,
                    name=name,
                    category=category,
                    location="Demo City",
                    account_id=merchant_account.id if merchant_account else None,
                    qr_code=f"FSQR:{merchant_id}",
                )
            )
        elif merchant.account_id is None:
            if merchant_account:
                merchant.account_id = merchant_account.id

    db.commit()


def ensure_runtime_schema() -> None:
    """Add missing columns for older local SQLite demo databases."""
    Base.metadata.create_all(bind=engine)
    if not str(engine.url).startswith("sqlite"):
        return

    columns: dict[str, dict[str, str]] = {
        "users": {
            "avatar": "VARCHAR",
            "upi_id": "VARCHAR",
        },
        "accounts": {
            "updated_at": "DATETIME",
        },
        "devices": {
            "browser": "VARCHAR",
        },
        "transactions": {
            "merchant_id": "VARCHAR",
            "description": "VARCHAR",
            "signals": "JSON",
            "explanation": "TEXT",
        },
        "alerts": {
            "alert_type": "VARCHAR",
            "details": "JSON",
            "read": "BOOLEAN DEFAULT 0",
        },
    }
    with engine.begin() as conn:
        for table, wanted in columns.items():
            existing = {
                row[1]
                for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            }
            for column_name, column_type in wanted.items():
                if column_name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"))


def fraud_score_for_transaction(db: Session, sender: User, receiver: User, amount: float, device_id: str | None) -> dict:
    profile = PROFILE_BY_ID.get(sender.user_id, {})
    base = {RiskLevel.LOW: 18, RiskLevel.MEDIUM: 42, RiskLevel.HIGH: 68}.get(profile.get("risk", RiskLevel.LOW), 24)
    recent_count = (
        db.query(Transaction)
        .filter(Transaction.sender_user_id == sender.id)
        .order_by(desc(Transaction.timestamp))
        .limit(6)
        .count()
    )
    reasons = []
    score = float(base)
    if amount >= 15000:
        score += 22
        reasons.append("Amount is much higher than this profile's normal payment range.")
    elif amount >= 7000:
        score += 12
        reasons.append("Amount is moderately higher than usual.")
    if recent_count >= 5:
        score += 10
        reasons.append("Several recent payments were found for this sender.")
    safe_device_id = scoped_device_id(sender, device_id)
    if safe_device_id and not db.query(Device).filter(Device.user_id == sender.id, Device.device_id == safe_device_id).first():
        score += 12
        reasons.append("Payment came from a new device.")
    if PROFILE_BY_ID.get(receiver.user_id, {}).get("risk") == RiskLevel.HIGH:
        score += 8
        reasons.append("Receiver profile has elevated historical risk.")

    model_hint = fraud_service.score_hint(sender.user_id, receiver.user_id, amount)
    if model_hint is not None:
        score = (score * 0.7) + (model_hint["fused_score"] * 100 * 0.3)
        if model_hint["flagged"]:
            reasons.append("Read-only hybrid model sample indicates a suspicious pattern.")

    score = max(1.0, min(score, 99.0))
    if score >= 76:
        status = TransactionStatus.BLOCKED
        level = RiskLevel.HIGH
        decision = "blocked"
    elif score >= 50:
        status = TransactionStatus.WARNING
        level = RiskLevel.MEDIUM
        decision = "flagged"
    else:
        status = TransactionStatus.COMPLETED
        level = RiskLevel.LOW
        decision = "approved"
    if not reasons:
        reasons.append("No strong anomaly found for this profile.")
    return {
        "score": round(score, 2),
        "level": level,
        "status": status,
        "decision": decision,
        "reasons": reasons,
        "model_hint": model_hint,
    }


def process_transfer(
    db: Session,
    sender: User,
    receiver: User,
    amount: float,
    pin: str,
    note: str = "",
    device_id: str | None = None,
    location: str | None = None,
    merchant_id: str | None = None,
) -> Transaction:
    if sender.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Sender profile is not active")
    if receiver.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Receiver profile is not active")
    if receiver.id == sender.id:
        raise HTTPException(status_code=400, detail="Cannot pay your own profile")
    if PAYMENT_PINS.get(sender.user_id) != pin:
        raise HTTPException(status_code=403, detail="Invalid payment PIN")

    sender_account = db.query(Account).filter(Account.user_id == sender.id).first()
    receiver_account = db.query(Account).filter(Account.user_id == receiver.id).first()
    if sender_account is None or receiver_account is None:
        raise HTTPException(status_code=409, detail="Wallet account is missing")
    if sender_account.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient FraudShield Money")

    fraud = fraud_score_for_transaction(db, sender, receiver, amount, device_id)
    tx = Transaction(
        transaction_id=f"FSM-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}",
        sender_user_id=sender.id,
        receiver_user_id=receiver.id,
        sender_account_id=sender_account.id,
        receiver_account_id=receiver_account.id,
        merchant_id=merchant_id,
        amount=round(float(amount), 2),
        currency="FSM",
        device_id=None,
        location=location or PROFILE_BY_ID.get(sender.user_id, {}).get("location"),
        description=note,
        status=fraud["status"],
        risk_score=fraud["score"],
        risk_level=fraud["level"],
        fraud_decision=fraud["decision"] != "approved",
        signals={"reasons": fraud["reasons"], "model_hint": fraud["model_hint"]},
        explanation="; ".join(fraud["reasons"]),
    )
    db.add(tx)

    if fraud["status"] != TransactionStatus.BLOCKED:
        sender_account.balance = round(float(sender_account.balance) - float(amount), 2)
        receiver_account.balance = round(float(receiver_account.balance) + float(amount), 2)

        if merchant_id and fraud["status"] == TransactionStatus.COMPLETED:
            cashback = min(round(float(amount) * 0.01, 2), 100.0)
            if cashback > 0:
                sender_account.balance = round(float(sender_account.balance) + cashback, 2)
                db.add(Reward(
                    user_id=sender.id,
                    transaction_id=tx.transaction_id,
                    amount=cashback,
                    reward_type="CASHBACK",
                    description="1% merchant payment cashback",
                ))
                tx.signals["cashback"] = cashback

    if fraud["decision"] != "approved":
        db.add(
            Alert(
                user_id=sender.id,
                transaction_id=tx.transaction_id,
                alert_type="HIGH_RISK_PAYMENT",
                severity="CRITICAL" if fraud["decision"] == "blocked" else "WARNING",
                message=f"Payment {fraud['decision']} by FraudShield.",
                details={"risk_score": fraud["score"], "reasons": fraud["reasons"]},
            )
        )
    return tx


def serialize_transaction(tx: Transaction) -> dict:
    return {
        "transaction_id": tx.transaction_id,
        "sender": tx.sender_user.name if tx.sender_user else "System",
        "receiver": tx.receiver_user.name if tx.receiver_user else "Unknown",
        "sender_user_id": tx.sender_user.user_id if tx.sender_user else None,
        "receiver_user_id": tx.receiver_user.user_id if tx.receiver_user else None,
        "amount": round(float(tx.amount), 2),
        "currency": "FSM",
        "note": tx.description or "",
        "status": tx.status.value if hasattr(tx.status, "value") else tx.status,
        "risk_score": round(float(tx.risk_score or 0), 2),
        "risk_level": tx.risk_level.value if hasattr(tx.risk_level, "value") else tx.risk_level,
        "reasons": tx.signals.get("reasons", []) if tx.signals else [],
        "cashback": round(float(tx.signals.get("cashback", 0)), 2) if tx.signals else 0,
        "created_at": tx.timestamp.isoformat() if tx.timestamp else None,
    }


def serialize_request(row: PaymentRequest, current_user: User | None = None) -> dict:
    direction = None
    if current_user is not None:
        direction = "incoming" if row.payer_user_id == current_user.id else "outgoing"
    return {
        "request_id": row.request_id,
        "requester": row.requester.name if row.requester else "Unknown",
        "payer": row.payer.name if row.payer else "Unknown",
        "requester_user_id": row.requester.user_id if row.requester else None,
        "payer_user_id": row.payer.user_id if row.payer else None,
        "amount": round(float(row.amount), 2),
        "currency": "FSM",
        "note": row.note or "",
        "status": row.status,
        "direction": direction,
        "transaction_id": row.transaction_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time payment and fraud events."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or process message
            message = json.loads(data)
            # Later phases will use this for live transaction updates
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============================================================================
# PLACEHOLDER ROUTERS (To be implemented in phases)
# ============================================================================

@app.get("/api/auth/test", tags=["Auth"])
async def test_auth():
    """Placeholder for authentication phase."""
    return {"message": "Auth phase coming soon", "phase": "B"}


@app.get("/api/payments/test", tags=["Payments"])
async def test_payments():
    """Placeholder for payments phase."""
    return {"message": "Payments phase coming soon", "phase": "E"}


@app.get("/api/analyst/test", tags=["Analyst"])
async def test_analyst():
    """Placeholder for analyst console phase."""
    return {"message": "Analyst phase coming soon", "phase": "I"}


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
