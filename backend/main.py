"""FastAPI application entrypoint for TraceLedger backend."""
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routes.batches import router as batches_router
from .routes.verification import router as verification_router
from .schemas import HealthResponse
from .services.blockchain import default_blockchain_service
from .services.storage import get_latest_batch, list_batches


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema is ready on startup."""
    init_db()
    yield


app = FastAPI(
    title="TraceLedger Backend API",
    description="Backend anchoring and verification service for MST Blockchain Buildathon",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(batches_router, prefix="/api")
app.include_router(batches_router)
app.include_router(verification_router, prefix="/api")
app.include_router(verification_router)


@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint reporting API and blockchain connectivity."""
    latest = get_latest_batch()
    _, total = list_batches(limit=1, offset=0)
    connected = default_blockchain_service.is_connected()

    return HealthResponse(
        status="ok",
        blockchain_connected=connected,
        contract_address=default_blockchain_service.contract_address,
        chain_id=default_blockchain_service.chain_id if connected else None,
        latest_batch_id=latest["batch_id"] if latest else 0,
        total_batches=total,
    )


# Serve frontend SPA if frontend/dist exists
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dist_dir = os.path.join(base_dir, "frontend", "dist")

if os.path.exists(dist_dir):
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def serve_root():
        return FileResponse(os.path.join(dist_dir, "index.html"))

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("batches/") or full_path == "health":
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = os.path.join(dist_dir, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(dist_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
