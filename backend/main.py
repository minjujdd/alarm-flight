from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional
import random

from fastapi import FastAPI
from sqlmodel import SQLModel, Field, Session, create_engine, select


# -------------------------
# 1. DB 테이블 정의
# -------------------------

class EventLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: str
    action: str
    score: float
    is_anomaly: bool


# 회원
# PostgreSQL 에서 user 는 예약어라서 테이블 이름을 users 로 지정
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    name: str
    phone: Optional[str] = None
    # 다중 계정 탐지용: 가입 당시 IP·기기 정보
    signup_ip: Optional[str] = Field(default=None, index=True)
    signup_device_id: Optional[str] = Field(default=None, index=True)
    is_blocked: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


# 쿠폰 (회원에게 발급된 쿠폰 1장 = 1행)
class Coupon(SQLModel, table=True):
    __tablename__ = "coupons"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    coupon_type: str = "signup"  # signup, event 등
    discount_amount: int
    issued_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    used_at: Optional[datetime] = None  # None 이면 미사용


# 항공편
class Flight(SQLModel, table=True):
    __tablename__ = "flights"

    id: Optional[int] = Field(default=None, primary_key=True)
    flight_no: str = Field(index=True)  # 예: AF101
    departure_airport: str  # 예: GMP
    arrival_airport: str  # 예: CJU
    departure_time: datetime = Field(index=True)
    arrival_time: datetime
    price: int
    total_seats: int
    remaining_seats: int
    # 특가 항공편 여부와 판매 시작 시각 (오픈 직후 선점 봇 탐지용)
    is_special: bool = False
    sale_open_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)


# 예약
class Reservation(SQLModel, table=True):
    __tablename__ = "reservations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    flight_id: int = Field(foreign_key="flights.id", index=True)
    seat_count: int = 1
    total_price: int
    coupon_id: Optional[int] = Field(default=None, foreign_key="coupons.id")
    # confirmed, captcha_required, blocked, cancelled
    status: str = "confirmed"
    risk_score: Optional[float] = None
    # 봇 탐지용: 예약 요청 당시 IP·기기 정보
    request_ip: Optional[str] = None
    device_id: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


# -------------------------
# 2. SQLite 연결
# -------------------------

# 실행 위치와 관계없이 항상 backend/app.db 를 사용
sqlite_file_name = Path(__file__).resolve().parent / "app.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {
    "check_same_thread": False
}

engine = create_engine(
    sqlite_url,
    connect_args=connect_args
)


# -------------------------
# 3. DB 테이블 생성
# -------------------------

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# -------------------------
# 4. FastAPI 실행
# -------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="AI 이상행동 탐지 API",
    lifespan=lifespan
)


# -------------------------
# 5. 테스트
# -------------------------

@app.get("/")
def root():
    return {
        "message": "졸프 백엔드 서버 실행 성공"
    }


# -------------------------
# 6. 로그 생성
# -------------------------

@app.post("/logs")
def create_log(log: EventLog):

    with Session(engine) as session:
        session.add(log)
        session.commit()
        session.refresh(log)

        return log


# -------------------------
# 7. 전체 로그 조회
# -------------------------

@app.get("/logs")
def get_logs():

    with Session(engine) as session:
        statement = select(EventLog)
        logs = session.exec(statement).all()

        return logs


# -------------------------
# 8. 이상 로그만 조회
# -------------------------

@app.get("/logs/anomalies")
def get_anomaly_logs():

    with Session(engine) as session:
        statement = select(EventLog).where(
            EventLog.is_anomaly == True
        )

        logs = session.exec(statement).all()

        return logs


# -------------------------
# 9. 로그 통계 조회
# -------------------------

@app.get("/stats")
def get_stats():

    with Session(engine) as session:
        statement = select(EventLog)
        logs = session.exec(statement).all()

        # 전체 로그 수
        total_logs = len(logs)

        # 이상 로그 수
        anomaly_logs = sum(
            1 for log in logs if log.is_anomaly
        )

        # 이상 비율
        if total_logs > 0:
            anomaly_rate = round(
                anomaly_logs / total_logs * 100, 1
            )
        else:
            anomaly_rate = 0

        return {
            "total_logs": total_logs,
            "anomaly_logs": anomaly_logs,
            "anomaly_rate": anomaly_rate
        }


# -------------------------
# 10. 특정 사용자 로그 조회
# -------------------------

@app.get("/logs/user/{user_id}")
def get_user_logs(user_id: str):

    with Session(engine) as session:
        statement = select(EventLog).where(
            EventLog.user_id == user_id
        )

        logs = session.exec(statement).all()

        return logs


# -------------------------
# 11. 임시 이상행동 탐지
# -------------------------

@app.post("/detect")
def detect(user_id: str, action: str):

    # 임시 AI 역할: 0~1 사이의 이상 점수를 생성
    score = round(random.random(), 2)

    # 0.7 이상이면 이상 행동으로 판정
    is_anomaly = score >= 0.7

    # 판정 결과를 로그로 생성
    log = EventLog(
        user_id=user_id,
        action=action,
        score=score,
        is_anomaly=is_anomaly
    )

    # DB에 저장
    with Session(engine) as session:
        session.add(log)
        session.commit()
        session.refresh(log)

        return log
