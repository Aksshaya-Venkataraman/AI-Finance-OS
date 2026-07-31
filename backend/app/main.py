from fastapi import FastAPI
app = FastAPI(
    title="AI Finance OS",
    version="1.0.0",
    descripition="Enterprisee Multi-Agent Finance Platform"
)
@app.get("/")
def home():
    return {
        "message": "Welcome to AI Finance OS"
    }
@app.get("/health")
def health():
    return {
        "status": "Healthy"
    }