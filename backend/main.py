from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from backend.config import settings
from backend.routers import auth, farmers, credit, verification, farms, fpo, passport, consent, lender, ml_router
from backend.database import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting KisanSetu — Farmer Trust Passport API")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    yield
    logger.info("Shutting down KisanSetu API")


app = FastAPI(
    title="KisanSetu — Farmer Trust Passport API",
    description=(
        "Portable Agricultural Economic Identity for transparent credit access. "
        "Farmer owns their data. FPO verifies. Lender decides. KisanSetu explains."
    ),
    version="1.0.0-mvp",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────
app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(farmers.router,      prefix="/api/v1/farmers",      tags=["Farmers"])
app.include_router(farms.router,        prefix="/api/v1/farmers",      tags=["Farms & Records"])
app.include_router(credit.router,       prefix="/api/v1/credit",       tags=["Credit Applications"])
app.include_router(verification.router, prefix="/api/v1/verification", tags=["Verification"])
app.include_router(fpo.router,          prefix="/api/v1/fpo",          tags=["FPO"])
app.include_router(passport.router,     prefix="/api/v1/passport",     tags=["Trust Passport"])
app.include_router(consent.router,      prefix="/api/v1/consent",      tags=["Consent & Data Ownership"])
app.include_router(lender.router,       prefix="/api/v1/lender",       tags=["Lender Portal"])
app.include_router(ml_router.router,    prefix="/api/v1/ml",            tags=["ML Intelligence"])


@app.get("/")
async def root():
    return {
        "message": "KisanSetu — Farmer Trust Passport API",
        "version": "1.0.0-mvp",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "KisanSetu Trust Passport API",
        "version": "1.0.0-mvp",
    }
