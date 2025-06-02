from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router
from conversational_agent import router as ws_router

app = FastAPI(
    title="IA Services API",
    description="API for authentication and conversational agent services",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(ws_router.router, prefix="/chat", tags=["Conversational Agent"])

@app.get("/")
async def root():
    return {"message": "Welcome to IA Services API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
