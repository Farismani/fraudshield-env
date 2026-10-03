"""
Vercel Serverless Function entry point for FraudShieldAI Pay API.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path so 'backend' can be resolved
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure database path is in writable /tmp directory on Vercel
if os.getenv("VERCEL"):
    os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/fraudshield_webapp.db")

from backend.app import app
