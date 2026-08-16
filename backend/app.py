"""
FraudShieldAI Pay - FastAPI Backend
Main application entry point for the synthetic payment ecosystem.

Run: uvicorn backend.app:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import json
from datetime import datetime

# Import database and models
from backend.database import create_tables, SessionLocal, engine
from backend.models.models import Base

# Import routers (will be created in phases)
# from backend.routers import auth, payments, users, accounts, devices, transactions, analyst, fraud

# Initialize database on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and cleanup on shutdown."""
    # Startup
    Base.metadata.create_all(bind=engine)
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
