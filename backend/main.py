from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import create_db_and_tables
from routers import coupons, flights, logs, reservations, users


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


# 서버 동작 확인
@app.get("/")
def root():
    return {
        "message": "졸프 백엔드 서버 실행 성공"
    }
