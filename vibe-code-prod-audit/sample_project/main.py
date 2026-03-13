"""A typical vibe-coded FastAPI project — minimal, no tests, no health check.

This is intentionally "production-unready" to demonstrate vibe-audit's capabilities.
"""
from fastapi import FastAPI

app = FastAPI(title="My Vibe App")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/users")
async def get_users():
    return [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]


@app.post("/users")
async def create_user(name: str):
    return {"id": 3, "name": name}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"id": user_id, "name": "Someone"}


@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    return {"deleted": True}
