from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import generation, library, health, workflow
from app.logging_config import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="GenMedia API")

logger.info("Starting GenMedia API application")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(health.router, tags=["health"])
app.include_router(generation.router, prefix="/generate", tags=["generation"])
app.include_router(library.router, prefix="/library", tags=["library"])
app.include_router(workflow.router, prefix="/workflows", tags=["workflows"])