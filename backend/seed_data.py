"""
Seed data for FraudShieldAI Pay.
Creates synthetic users, accounts, devices, merchants, and transactions.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import random
import json

from backend.models.models import (
    User, Account, Device, Session as DBSession, Beneficiary, Merchant,
    Transaction, Alert, TransactionStatus, RiskLevel, AccountType, DeviceStatus,
    Card, Wallet, Reward, UserStatus
)


def seed_users(db: Session):
    """Create synthetic users."""
    users_data = [
        {
            "user_id": "faris",
            "name": "Faris",
            "email": "faris@fsaipay.local",
            "phone": "+91-9876543210",
            "avatar": "👨‍💼",
            "password_hash": "hashed_password_faris",
            "upi_id": "faris@fsaipay",
        },
        {
            "user_id": "rahul",
            "name": "Rahul",
            "email": "rahul@fsaipay.local",
            "phone": "+91-9876543211",
            "avatar": "👨‍💻",
            "password_hash": "hashed_password_rahul",
            "upi_id": "rahul@fsaipay",
        },
        {
            "user_id": "ahmed",
            "name": "Ahmed",
            "email": "ahmed@fsaipay.local",
            "phone": "+91-9876543212",
            "avatar": "👨",
            "password_hash": "hashed_password_ahmed",
            "upi_id": "ahmed@fsaipay",
        },
        {
            "user_id": "priya",
            "name": "Priya",
            "email": "priya@fsaipay.local",
            "phone": "+91-9876543213",
            "avatar": "👩‍💼",
            "password_hash": "hashed_password_priya",
            "upi_id": "priya@fsaipay",
        },
        {
            "user_id": "ananya",
            "name": "Ananya",
            "email": "ananya@fsaipay.local",
            "phone": "+91-9876543214",
            "avatar": "👩‍💻",
            "password_hash": "hashed_password_ananya",
            "upi_id": "ananya@fsaipay",
        },
        {
            "user_id": "arjun",
            "name": "Arjun",
            "email": "arjun@fsaipay.local",
            "phone": "+91-9876543215",
            "avatar": "👨‍🎨",
            "password_hash": "hashed_password_arjun",
            "upi_id": "arjun@fsaipay",
        },
        {
            "user_id": "kiran",
            "name": "Kiran",
            "email": "kiran@fsaipay.local",
            "phone": "+91-9876543216",
            "avatar": "👩",
            "password_hash": "hashed_password_kiran",
            "upi_id": "kiran@fsaipay",
        },
        {
            "user_id": "neha",
            "name": "Neha",
            "email": "neha@fsaipay.local",
            "phone": "+91-9876543217",
            "avatar": "👩‍🔬",
            "password_hash": "hashed_password_neha",
            "upi_id": "neha@fsaipay",
        },
        {
            "user_id": "analyst",
            "name": "Security Analyst",
            "email": "analyst@fsaipay.local",
            "phone": "+91-9999999999",
            "avatar": "🔍",
            "password_hash": "hashed_password_analyst",
            "upi_id": "analyst@fsaipay",
            "status": UserStatus.ACTIVE,
        },
    ]

    users = []
    for data in users_data:
        user = User(**data)
        db.add(user)
        db.flush()
        users.append(user)

    db.commit()
    return {u.user_id: u for u in users}


def seed_accounts(db: Session, users_map):
    """Create synthetic accounts for each user."""
    accounts = []

    account_configs = {
        "faris": [
            {"type": AccountType.CHECKING, "balance": 25000},
            {"type": AccountType.SAVINGS, "balance": 50000},
        ],
        "rahul": [
            {"type": AccountType.CHECKING, "balance": 18000},
        ],
        "ahmed": [
            {"type": AccountType.CHECKING, "balance": 32000},
        ],
        "priya": [
            {"type": AccountType.CHECKING, "balance": 42000},
        ],
        "ananya": [
            {"type": AccountType.CHECKING, "balance": 15000},
        ],
        "arjun": [
            {"type": AccountType.CHECKING, "balance": 28000},
        ],
        "kiran": [
            {"type": AccountType.CHECKING, "balance": 35000},
        ],
        "neha": [
            {"type": AccountType.CHECKING, "balance": 22000},
        ],
        "analyst": [
            {"type": AccountType.WALLET, "balance": 0},
        ],
    }

    for user_id, configs in account_configs.items():
        user = users_map[user_id]
        for i, cfg in enumerate(configs):
            account = Account(
                account_id=f"ACC_{user_id.upper()}_{i+1:02d}",
                user_id=user.id,
                account_type=cfg["type"],
                balance=cfg["balance"],
                status="ACTIVE",
            )
            db.add(account)
            accounts.append(account)

    db.commit()
    return accounts


def seed_devices(db: Session, users_map):
    """Create synthetic devices for users."""
    devices = []

    device_configs = {
        "faris": [
            {
                "device_name": "iPhone 15 Pro",
                "device_type": "iOS",
                "os": "iOS 17.0",
                "browser": "Safari",
                "ip_address": "192.168.1.100",
                "location": "Mysuru, KA",
                "trusted": True,
                "status": DeviceStatus.TRUSTED,
            },
            {
                "device_name": "Windows Chrome",
                "device_type": "Web",
                "os": "Windows 11",
                "browser": "Chrome",
                "ip_address": "192.168.1.101",
                "location": "Mysuru, KA",
                "trusted": True,
                "status": DeviceStatus.TRUSTED,
            },
        ],
        "rahul": [
            {
                "device_name": "Samsung Galaxy S23",
                "device_type": "Android",
                "os": "Android 14",
                "browser": "Chrome",
                "ip_address": "192.168.1.110",
                "location": "Bengaluru, KA",
                "trusted": True,
                "status": DeviceStatus.TRUSTED,
            },
        ],
        "ahmed": [
            {
                "device_name": "Google Pixel 7",
                "device_type": "Android",
                "os": "Android 14",
                "browser": "Chrome",
                "ip_address": "192.168.1.120",
                "location": "Pune, MH",
                "trusted": True,
                "status": DeviceStatus.TRUSTED,
            },
        ],
        "priya": [
            {
                "device_name": "MacBook Pro",
                "device_type": "Web",
                "os": "macOS 13",
                "browser": "Safari",
                "ip_address": "192.168.1.130",
                "location": "Mumbai, MH",
                "trusted": True,
                "status": DeviceStatus.TRUSTED,
            },
        ],
        "ananya": [
            {
                "device_name": "iPad Air",
                "device_type": "iOS",
                "os": "iPadOS 17.0",
                "browser": "Safari",
                "ip_address": "192.168.1.140",
                "location": "Delhi, DL",
                "trusted": True,
                "status": DeviceStatus.TRUSTED,
            },
        ],
        "arjun": [
            {
                "device_name": "OnePlus 12",
                "device_type": "Android",
                "os": "Android 14",
                "browser": "Chrome",
                "ip_address": "192.168.1.150",
                "location": "Hyderabad, TG",
                "trusted": True,
                "status": DeviceStatus.TRUSTED,
            },
        ],
        "kiran": [
            {
                "device_name": "iPhone 14",
                "device_type": "iOS",
                "os": "iOS 17.0",
                "browser": "Safari",
                "ip_address": "192.168.1.160",
                "location": "Bangalore, KA",
                "trusted": True,
                "status": DeviceStatus.TRUSTED,
            },
        ],
        "neha": [
            {
                "device_name": "Xiaomi 13",
                "device_type": "Android",
                "os": "Android 13",
                "browser": "Chrome",
                "ip_address": "192.168.1.170",
                "location": "Chennai, TN",
                "trusted": True,
                "status": DeviceStatus.TRUSTED,
            },
        ],
    }

    for user_id, configs in device_configs.items():
        user = users_map[user_id]
        for i, cfg in enumerate(configs):
            device = Device(
                device_id=f"DEV_{user_id.upper()}_{i+1:02d}",
                user_id=user.id,
                **cfg,
            )
            db.add(device)
            devices.append(device)

    db.commit()
    return devices


def seed_merchants(db: Session):
    """Create synthetic merchants."""
    merchants_data = [
        {
            "merchant_id": "MERCHANT_001",
            "name": "Mysuru Cafe",
            "category": "Food & Beverages",
            "location": "Mysuru, KA",
            "qr_code": "FSQR_MERCHANT_001_200",
        },
        {
            "merchant_id": "MERCHANT_002",
            "name": "Tech World",
            "category": "Electronics",
            "location": "Bengaluru, KA",
            "qr_code": "FSQR_MERCHANT_002_200",
        },
        {
            "merchant_id": "MERCHANT_003",
            "name": "SuperMart",
            "category": "Grocery",
            "location": "Mysuru, KA",
            "qr_code": "FSQR_MERCHANT_003_200",
        },
        {
            "merchant_id": "MERCHANT_004",
            "name": "Fuel Station",
            "category": "Fuel",
            "location": "Mysuru, KA",
            "qr_code": "FSQR_MERCHANT_004_200",
        },
        {
            "merchant_id": "MERCHANT_005",
            "name": "Online Store",
            "category": "E-Commerce",
            "location": "Delhi, DL",
            "qr_code": "FSQR_MERCHANT_005_200",
        },
    ]

    merchants = []
    for data in merchants_data:
        merchant = Merchant(**data)
        db.add(merchant)
        merchants.append(merchant)

    db.commit()
    return merchants


def seed_beneficiaries(db: Session, users_map):
    """Create beneficiary relationships."""
    beneficiaries = []

    # Create mutual beneficiaries between users
    user_pairs = [
        ("faris", "rahul"),
        ("faris", "ahmed"),
        ("rahul", "priya"),
        ("ahmed", "ananya"),
        ("priya", "arjun"),
    ]

    for user_id1, user_id2 in user_pairs:
        user1 = users_map[user_id1]
        user2 = users_map[user_id2]

        # user1 -> user2
        ben1 = Beneficiary(
            beneficiary_id=f"BEN_{user_id1.upper()}_TO_{user_id2.upper()}",
            owner_user_id=user1.id,
            receiver_user_id=user2.id,
            nickname=f"{user2.name}",
            trusted=True,
            status="TRUSTED",
        )
        beneficiaries.append(ben1)
        db.add(ben1)

        # user2 -> user1
        ben2 = Beneficiary(
            beneficiary_id=f"BEN_{user_id2.upper()}_TO_{user_id1.upper()}",
            owner_user_id=user2.id,
            receiver_user_id=user1.id,
            nickname=f"{user1.name}",
            trusted=True,
            status="TRUSTED",
        )
        beneficiaries.append(ben2)
        db.add(ben2)

    db.commit()
    return beneficiaries


def seed_transactions(db: Session, users_map, accounts_list):
    """Create sample historical transactions."""
    transactions = []

    # Simple P2P transactions
    user_ids = ["faris", "rahul", "ahmed", "priya"]
    num_transactions = 20

    for i in range(num_transactions):
        sender_id = random.choice(user_ids)
        receiver_id = random.choice([u for u in user_ids if u != sender_id])

        sender_user = users_map[sender_id]
        receiver_user = users_map[receiver_id]

        # Get first account of each user
        sender_account = next(acc for acc in accounts_list if acc.user_id == sender_user.id)
        receiver_account = next(acc for acc in accounts_list if acc.user_id == receiver_user.id)

        amount = round(random.uniform(100, 5000), 2)
        risk_score = round(random.uniform(0.0, 0.5), 4)

        tx = Transaction(
            transaction_id=f"PAY-{1000 + i:06d}",
            sender_user_id=sender_user.id,
            receiver_user_id=receiver_user.id,
            sender_account_id=sender_account.id,
            receiver_account_id=receiver_account.id,
            amount=amount,
            location=sender_account.user.accounts[0].user.devices[0].location if sender_account.user.devices else "Unknown",
            status=TransactionStatus.COMPLETED,
            risk_score=risk_score,
            risk_level=RiskLevel.LOW if risk_score < 0.3 else RiskLevel.MEDIUM if risk_score < 0.7 else RiskLevel.HIGH,
            fraud_decision=False,
            timestamp=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
        )
        transactions.append(tx)
        db.add(tx)

    db.commit()
    return transactions


def seed_database():
    """Run all seeding functions."""
    from backend.database import SessionLocal, create_tables

    # Create tables
    create_tables()

    db = SessionLocal()
    try:
        print("Seeding users...")
        users_map = seed_users(db)

        print("Seeding accounts...")
        accounts = seed_accounts(db, users_map)

        print("Seeding devices...")
        devices = seed_devices(db, users_map)

        print("Seeding merchants...")
        merchants = seed_merchants(db)

        print("Seeding beneficiaries...")
        beneficiaries = seed_beneficiaries(db, users_map)

        print("Seeding transactions...")
        transactions = seed_transactions(db, users_map, accounts)

        print("\n✓ Database seeded successfully!")
        print(f"  - {len(users_map)} users")
        print(f"  - {len(accounts)} accounts")
        print(f"  - {len(devices)} devices")
        print(f"  - {len(merchants)} merchants")
        print(f"  - {len(beneficiaries)} beneficiaries")
        print(f"  - {len(transactions)} transactions")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
