from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import generation, library, health

app = FastAPI(title="GenMedia API")

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