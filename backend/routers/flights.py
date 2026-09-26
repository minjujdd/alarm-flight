from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Flight, FlightCreate


router = APIRouter(tags=["항공편"])


# 항공편 등록 (관리자·테스트용)
@router.post("/flights")
def create_flight(data: FlightCreate, session: Session = Depends(get_session)):

    flight = Flight(
        **data.model_dump(),
        remaining_seats=data.total_seats
    )
    session.add(flight)
    session.commit()
    session.refresh(flight)

    return flight


# 항공편 검색
@router.get("/flights")
def search_flights(
    departure_airport: Optional[str] = None,
    arrival_airport: Optional[str] = None,
    special_only: bool = False,
    session: Session = Depends(get_session)
):

    statement = select(Flight)

    if departure_airport:
        statement = statement.where(
            Flight.departure_airport == departure_airport
        )
    if arrival_airport:
        statement = statement.where(
            Flight.arrival_airport == arrival_airport
        )
    if special_only:
        statement = statement.where(Flight.is_special == True)

    return session.exec(statement).all()


# 항공편 상세 조회
@router.get("/flights/{flight_id}")
def get_flight(flight_id: int, session: Session = Depends(get_session)):

    flight = session.get(Flight, flight_id)

    if not flight:
        raise HTTPException(404, "항공편을 찾을 수 없습니다")

    return flight
