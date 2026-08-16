"""
SQLAlchemy ORM models for FraudShieldAI Pay.
Synthetic payment ecosystem data structures.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey,
    Enum as SQLEnum, Text, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
import uuid

from backend.database import Base


def generate_id():
    """Generate unique IDs."""
    return str(uuid.uuid4())[:12].upper()


# ============================================================================
# ENUMS
# ============================================================================


class AccountType(str, enum.Enum):
    SAVINGS = "SAVINGS"
    CHECKING = "CHECKING"
    WALLET = "WALLET"


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    WARNING = "WARNING"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DeviceStatus(str, enum.Enum):
    TRUSTED = "TRUSTED"
    NEW = "NEW"
    SUSPICIOUS = "SUSPICIOUS"
    BLOCKED = "BLOCKED"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    BLOCKED = "BLOCKED"


# ============================================================================
# CORE MODELS
# ============================================================================


class User(Base):
    """Synthetic user in FraudShieldAI Pay ecosystem."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, unique=True, nullable=False)  # e.g., "USER_001", "faris"
    name = Column(String, nullable=False)
    email = Column(String, unique=True)
    phone = Column(String, unique=True)
    avatar = Column(String)  # URL or emoji
    password_hash = Column(String, nullable=False)
    upi_id = Column(String, unique=True)  # e.g., "faris@fsaipay"
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    beneficiaries_owned = relationship("Beneficiary", foreign_keys="Beneficiary.owner_user_id", back_populates="owner_user")
    transactions_sent = relationship("Transaction", foreign_keys="Transaction.sender_user_id", back_populates="sender_user")
    transactions_received = relationship("Transaction", foreign_keys="Transaction.receiver_user_id", back_populates="receiver_user")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.user_id}>"


class Account(Base):
    """Synthetic bank account for a user."""
    __tablename__ = "accounts"

    id = Column(String, primary_key=True, default=generate_id)
    account_id = Column(String, unique=True, nullable=False)  # e.g., "ACC_001"
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    account_type = Column(SQLEnum(AccountType), default=AccountType.SAVINGS)
    balance = Column(Float, default=0.0)
    currency = Column(String, default="INR")
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions_sent = relationship("Transaction", foreign_keys="Transaction.sender_account_id", back_populates="sender_account")
    transactions_received = relationship("Transaction", foreign_keys="Transaction.receiver_account_id", back_populates="receiver_account")

    def __repr__(self):
        return f"<Account {self.account_id} balance={self.balance}>"


class Device(Base):
    """Device used to access the payment app."""
    __tablename__ = "devices"

    id = Column(String, primary_key=True, default=generate_id)
    device_id = Column(String, unique=True, nullable=False)  # e.g., "DEV_001"
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    device_name = Column(String)  # e.g., "iPhone 15 Pro"
    device_type = Column(String)  # e.g., "iOS", "Android", "Web"
    os = Column(String)
    browser = Column(String)
    ip_address = Column(String)
    location = Column(String)  # e.g., "Mysuru, KA"
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    trusted = Column(Boolean, default=False)
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.NEW)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="devices")
    sessions = relationship("Session", back_populates="device")
    transactions = relationship("Transaction", back_populates="device")

    def __repr__(self):
        return f"<Device {self.device_id} {self.device_name}>"


class Session(Base):
    """User login session."""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=generate_id)
    session_id = Column(String, unique=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    device_id = Column(String, ForeignKey("devices.id"), nullable=False)
    login_time = Column(DateTime, default=datetime.utcnow)
    logout_time = Column(DateTime)
    ip_address = Column(String)
    location = Column(String)
    status = Column(String, default="ACTIVE")  # ACTIVE, LOGGED_OUT, REVOKED

    # Relationships
    user = relationship("User", back_populates="sessions")
    device = relationship("Device", back_populates="sessions")

    def __repr__(self):
        return f"<Session {self.session_id}>"


class Beneficiary(Base):
    """Known or unknown payment recipient."""
    __tablename__ = "beneficiaries"

    id = Column(String, primary_key=True, default=generate_id)
    beneficiary_id = Column(String, unique=True, nullable=False)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    receiver_user_id = Column(String, ForeignKey("users.id"), nullable=True)  # NULL if unknown/merchant
    nickname = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    trusted = Column(Boolean, default=False)
    status = Column(String, default="NEW")  # NEW, TRUSTED, SUSPICIOUS, BLOCKED

    # Relationships
    owner_user = relationship("User", foreign_keys=[owner_user_id], back_populates="beneficiaries_owned")
    receiver_user = relationship("User", foreign_keys=[receiver_user_id], overlaps="beneficiaries_owned")

    def __repr__(self):
        return f"<Beneficiary {self.beneficiary_id}>"


class Merchant(Base):
    """Synthetic merchant for QR payments."""
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, default=generate_id)
    merchant_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String)  # e.g., "Cafe", "Store", "Fuel"
    location = Column(String)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    qr_code = Column(String)  # encoded QR data
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transactions = relationship("Transaction", back_populates="merchant")

    def __repr__(self):
        return f"<Merchant {self.merchant_id}>"


class Transaction(Base):
    """Payment transaction in the ecosystem."""
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=generate_id)
    transaction_id = Column(String, unique=True, nullable=False)  # e.g., "PAY-001"
    sender_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    receiver_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    sender_account_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    receiver_account_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=True)
    beneficiary_id = Column(String, ForeignKey("beneficiaries.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    device_id = Column(String, ForeignKey("devices.id"), nullable=True)
    location = Column(String)
    description = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(SQLEnum(RiskLevel), default=RiskLevel.LOW)
    fraud_decision = Column(Boolean, default=False)  # True if blocked/flagged
    scenario = Column(String)  # e.g., "ACCOUNT_TAKEOVER", "HIGH_VELOCITY", None for normal
    signals = Column(JSON, default=dict)  # Fraud signals that triggered decision
    explanation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sender_user = relationship("User", foreign_keys=[sender_user_id], back_populates="transactions_sent")
    receiver_user = relationship("User", foreign_keys=[receiver_user_id], back_populates="transactions_received")
    sender_account = relationship("Account", foreign_keys=[sender_account_id], back_populates="transactions_sent")
    receiver_account = relationship("Account", foreign_keys=[receiver_account_id], back_populates="transactions_received")
    device = relationship("Device", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction {self.transaction_id}>"


class Alert(Base):
    """Security alert for suspicious activity."""
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=True)
    alert_type = Column(String)  # e.g., "NEW_DEVICE", "UNUSUAL_LOCATION", "HIGH_RISK_PAYMENT"
    severity = Column(String)  # INFO, WARNING, CRITICAL
    message = Column(String)
    details = Column(JSON)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="alerts")

    def __repr__(self):
        return f"<Alert {self.alert_type}>"


# ============================================================================
# Additional Models for Features
# ============================================================================


class Wallet(Base):
    """User's simulated wallet."""
    __tablename__ = "wallets"

    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    balance = Column(Float, default=0.0)
    currency = Column(String, default="INR")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Card(Base):
    """Simulated payment card."""
    __tablename__ = "cards"

    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    card_id = Column(String, unique=True, nullable=False)
    card_type = Column(String)  # CREDIT, DEBIT, PREPAID
    provider = Column(String)  # VISA, MASTERCARD
    last_four = Column(String)  # ••••1024
    expiry = Column(String)  # MM/YY
    cvv = Column(String)  # Masked
    is_preferred = Column(Boolean, default=False)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)


class AutoPay(Base):
    """Recurring payment schedule."""
    __tablename__ = "autopays"

    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    beneficiary_id = Column(String, ForeignKey("beneficiaries.id"), nullable=False)
    amount = Column(Float, nullable=False)
    frequency = Column(String)  # DAILY, WEEKLY, MONTHLY
    next_payment = Column(DateTime)
    status = Column(String, default="ACTIVE")  # ACTIVE, PAUSED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)


class SplitExpense(Base):
    """Shared expense split between users."""
    __tablename__ = "split_expenses"

    id = Column(String, primary_key=True, default=generate_id)
    split_id = Column(String, unique=True, nullable=False)
    creator_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    description = Column(String)
    total_amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    participants = Column(JSON)  # List of user_ids and their share
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)


class Reward(Base):
    """Simulated rewards/cashback."""
    __tablename__ = "rewards"

    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=True)
    amount = Column(Float)
    reward_type = Column(String)  # CASHBACK, POINTS, BONUS
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Bill(Base):
    """Simulated bill for payment."""
    __tablename__ = "bills"

    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    provider = Column(String)  # Electricity, Water, etc.
    account_number = Column(String)
    amount = Column(Float)
    due_date = Column(DateTime)
    status = Column(String, default="PENDING")  # PENDING, PAID, OVERDUE
    created_at = Column(DateTime, default=datetime.utcnow)


class Recharge(Base):
    """Simulated recharge/top-up."""
    __tablename__ = "recharges"

    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    category = Column(String)  # Mobile, DTH, FASTag
    provider = Column(String)
    number = Column(String)  # Phone, DTH, etc.
    amount = Column(Float)
    status = Column(String, default="COMPLETED")
    created_at = Column(DateTime, default=datetime.utcnow)


class ScenarioEvent(Base):
    """Events triggered by scenario engine for fraud testing."""
    __tablename__ = "scenario_events"

    id = Column(String, primary_key=True, default=generate_id)
    scenario_name = Column(String)  # ACCOUNT_TAKEOVER, FRAUD_RING, etc.
    event_type = Column(String)
    involved_users = Column(JSON)
    involved_transactions = Column(JSON)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
