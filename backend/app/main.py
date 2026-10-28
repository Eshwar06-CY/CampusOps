from fastapi import FastAPI

app = FastAPI(
    title="CampusOps API",
    version="0.1.0",
    description="CampusOps event operations management backend",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}

