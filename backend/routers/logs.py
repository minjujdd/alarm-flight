import random

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from database import get_session
from models import EventLog


router = APIRouter(tags=["관리자: 로그·통계"])


# 로그 생성
@router.post("/logs")
def create_log(log: EventLog, session: Session = Depends(get_session)):

    session.add(log)
    session.commit()
    session.refresh(log)

    return log


# 전체 로그 조회
@router.get("/logs")
def get_logs(session: Session = Depends(get_session)):

    return session.exec(select(EventLog)).all()


# 이상 로그만 조회
@router.get("/logs/anomalies")
def get_anomaly_logs(session: Session = Depends(get_session)):

    statement = select(EventLog).where(
        EventLog.is_anomaly == True
    )

    return session.exec(statement).all()


# 로그 통계 조회
@router.get("/stats")
def get_stats(session: Session = Depends(get_session)):

    logs = session.exec(select(EventLog)).all()

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


# 특정 사용자 로그 조회
@router.get("/logs/user/{user_id}")
def get_user_logs(user_id: str, session: Session = Depends(get_session)):

    statement = select(EventLog).where(
        EventLog.user_id == user_id
    )

    return session.exec(statement).all()


# 임시 이상행동 탐지
@router.post("/detect")
def detect(user_id: str, action: str, session: Session = Depends(get_session)):

    # 임시 AI 역할: 0~1 사이의 이상 점수를 생성
    score = round(random.random(), 2)

    # 0.7 이상이면 이상 행동으로 판정
    is_anomaly = score >= 0.7

    log = EventLog(
        user_id=user_id,
        action=action,
        score=score,
        is_anomaly=is_anomaly
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    return log
