from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from database import create_db_and_tables
from routers import coupons, demo, flights, logs, reservations, users


# 시연용 API(/demo) 사용 여부. 끄려면 DEMO_MODE=0
DEMO_MODE = os.getenv("DEMO_MODE", "1") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="AI 이상행동 탐지 API",
    lifespan=lifespan
)

app.include_router(users.router)
app.include_router(flights.router)
app.include_router(coupons.router)
app.include_router(reservations.router)
app.include_router(logs.router)

if DEMO_MODE:
    app.include_router(demo.router)


# 서버 동작 확인
@app.get("/")
def root():
    return {
        "message": "졸프 백엔드 서버 실행 성공"
    }
