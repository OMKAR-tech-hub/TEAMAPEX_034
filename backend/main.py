from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from backend.config import settings
from backend.routers import farmers, credit, verification, auth
from backend.database import engine, Base

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Farmer Trust Passport application")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    yield
    # Shutdown
    logger.info("Shutting down application")


app = FastAPI(
    title="Farmer Trust Passport API",
    description="Portable Agricultural Economic Identity for transparent credit access",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(farmers.router, prefix="/api/v1/farmers", tags=["Farmers"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(credit.router, prefix="/api/v1/credit", tags=["Credit"])
app.include_router(verification.router, prefix="/api/v1/verification", tags=["Verification"])

# Serve uploaded profile photos
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Farmer Trust Passport API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
