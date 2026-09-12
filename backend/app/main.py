from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, bank, consents, farmers, fpo, loans, passports, risk, settlements, underwrite
from app.core.config import settings
from app.core.database import Base, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Kisan Setu baseline")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")
    yield
    logger.info("Shutting down Kisan Setu baseline")


app = FastAPI(
    title=settings.APP_NAME,
    description="Kisan Setu - Farmer Trust Passport monolith baseline",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(farmers.router, prefix="/api/v1/farmers", tags=["Farmers"])
app.include_router(fpo.router, prefix="/api/v1/fpo", tags=["FPO"])
app.include_router(passports.router, prefix="/api/v1/passports", tags=["Passports"])
app.include_router(consents.router, prefix="/api/v1/consents", tags=["Consents"])
app.include_router(consents.router, prefix="/api/v1/consent", include_in_schema=False)
app.include_router(bank.router, prefix="/api/v1/bank", tags=["Bank"])
app.include_router(bank.router, prefix="/api/v1/lender", include_in_schema=False)
app.include_router(underwrite.router, prefix="/api/v1/underwrite", tags=["Underwrite"])
app.include_router(loans.router, prefix="/api/v1/loans", tags=["Loans"])
app.include_router(settlements.router, prefix="/api/v1/settlements", tags=["Settlements"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk"])

os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {"message": "Kisan Setu API", "version": settings.APP_VERSION, "status": "operational"}


@app.get("/health")
def health():
    return {"status": "healthy"}