"""
Main Application Entry Point
----------------------------
SYS AI Lecturer Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import models, database
from app.routes import auth, courses, assessments, resources, admin, curriculum, reporting

# Create DB tables (Alembic recommended for production migrations)
models.Base.metadata.create_all(bind=database.engine)

# Initialize FastAPI app
app = FastAPI(
    title="SYS AI Lecturer System",
    description="Backend APIs for Student & Admin modules",
    version="1.0.0"
)

# =========================
# Middleware
# =========================
origins = [
    "http://localhost:3000",   # React/Next.js frontend
    "http://127.0.0.1:3000",
    "https://your-production-domain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PUT, DELETE
    allow_headers=["*"],
)

# =========================
# Routers
# =========================
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(assessments.router)
app.include_router(resources.router)
app.include_router(admin.router)
app.include_router(curriculum.router)
app.include_router(reporting.router)

# =========================
# Health Check
# =========================
@app.get("/", tags=["Health"])
def root():
    return {"message": "SYS AI Lecturer Backend is running"}
