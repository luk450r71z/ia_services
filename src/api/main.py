import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth.router import auth_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Include auth router
logger.info("Registering auth router at /api prefix")
app.include_router(auth_router, prefix="/api", tags=["Authentication"])
#app.include_router(chat_router, prefix="/conversational_agent", tags=["Conversational Agent"])

@app.get("/")
async def root():
    return {"message": "Welcome to IA Services API"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting API server")
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["auth"]
    )
