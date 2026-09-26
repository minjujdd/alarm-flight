from typing import Optional
import random

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from database import get_session
from events import client_ip, write_log
from models import EventLog, LogCreate, User


router = APIRouter(tags=["관리자: 로그·통계"])


def check_user(session: Session, user_id: Optional[int]):
    if user_id is not None and not session.get(User, user_id):
        raise HTTPException(404, "회원을 찾을 수 없습니다")


# 로그 직접 생성 (프론트에서 화면 이동 등 행동을 남길 때)
@router.post("/logs", response_model=EventLog)
def create_log(
    data: LogCreate,
    request: Request,
    ip: Optional[str] = Depends(client_ip),
    session: Session = Depends(get_session)
):

    check_user(session, data.user_id)

    log = write_log(
        session, ip=ip,
        user_agent=request.headers.get("user-agent"),
        **data.model_dump()
    )
    session.commit()
    session.refresh(log)

    return log


# 전체 로그 조회 (최신순)
@router.get("/logs", response_model=list[EventLog])
def get_logs(
    action: Optional[str] = None,
    limit: int = 100,
    session: Session = Depends(get_session)
):

    statement = select(EventLog)

    if action:
        statement = statement.where(EventLog.action == action)

    statement = statement.order_by(EventLog.id.desc()).limit(limit)

    return session.exec(statement).all()


# 이상 로그만 조회 (최신순)
@router.get("/logs/anomalies", response_model=list[EventLog])
def get_anomaly_logs(
    limit: int = 100,
    session: Session = Depends(get_session)
):

    statement = (
        select(EventLog)
        .where(EventLog.is_anomaly == True)
        .order_by(EventLog.id.desc())
        .limit(limit)
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


# 특정 사용자 로그 조회 (최신순)
@router.get("/logs/user/{user_id}", response_model=list[EventLog])
def get_user_logs(user_id: int, session: Session = Depends(get_session)):

    statement = (
        select(EventLog)
        .where(EventLog.user_id == user_id)
        .order_by(EventLog.id.desc())
    )

    return session.exec(statement).all()


# 임시 이상행동 탐지 (초기 테스트용, 실제 탐지는 POST /reservations 에서 수행)
@router.post("/detect", response_model=EventLog, deprecated=True)
def detect(
    user_id: int,
    action: str,
    session: Session = Depends(get_session)
):

    check_user(session, user_id)

    # 임시 AI 역할: 0~1 사이의 이상 점수를 생성
    score = round(random.random(), 2)

    log = write_log(
        session, action,
        user_id=user_id,
        ai_score=score,
        risk_score=score * 100,
        # 0.7 이상이면 이상 행동으로 판정
        is_anomaly=score >= 0.7,
        message="임시 랜덤 점수"
    )
    session.commit()
    session.refresh(log)

    return log
