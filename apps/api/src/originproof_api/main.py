from fastapi import FastAPI

app = FastAPI(title="OriginProof API", version="0.1.0")


@app.get("/health/live", tags=["health"])
async def live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready", tags=["health"])
async def ready() -> dict[str, str]:
    # Dependency readiness checks are added with the DB, Redis, and Chain adapters.
    return {"status": "ready"}
