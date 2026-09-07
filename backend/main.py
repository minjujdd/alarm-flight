from datetime import datetime
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
    action: strr
    score: float
    is_anomaly: bool


# -------------------------
# 2. SQLite 연결
# -------------------------

sqlite_file_name = "app.db"
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

app = FastAPI(
    title="AI 이상행동 탐지 API"
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


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
# 8. 임시 이상행동 탐지
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