from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from database import get_session
from models import Coupon, Flight, Reservation, ReservationRequest, User


router = APIRouter(tags=["예약"])


# 예약 (+ 쿠폰 사용)
@router.post("/reservations")
def create_reservation(
    data: ReservationRequest,
    request: Request,
    session: Session = Depends(get_session)
):

    now = datetime.now()

    user = session.get(User, data.user_id)
    if not user:
        raise HTTPException(404, "회원을 찾을 수 없습니다")
    if user.is_blocked:
        raise HTTPException(403, "차단된 회원입니다")

    flight = session.get(Flight, data.flight_id)
    if not flight:
        raise HTTPException(404, "항공편을 찾을 수 없습니다")
    if flight.sale_open_at and now < flight.sale_open_at:
        raise HTTPException(400, "아직 판매가 시작되지 않았습니다")
    if data.seat_count < 1:
        raise HTTPException(400, "좌석 수는 1 이상이어야 합니다")
    if flight.remaining_seats < data.seat_count:
        raise HTTPException(400, "잔여 좌석이 부족합니다")

    total_price = flight.price * data.seat_count

    coupon = None
    if data.coupon_id is not None:
        coupon = session.get(Coupon, data.coupon_id)
        if not coupon or coupon.user_id != user.id:
            raise HTTPException(400, "사용할 수 없는 쿠폰입니다")
        if coupon.used_at:
            raise HTTPException(400, "이미 사용한 쿠폰입니다")
        if coupon.expires_at and now > coupon.expires_at:
            raise HTTPException(400, "만료된 쿠폰입니다")

        total_price = max(total_price - coupon.discount_amount, 0)
        coupon.used_at = now
        session.add(coupon)

    flight.remaining_seats -= data.seat_count
    session.add(flight)

    reservation = Reservation(
        user_id=user.id,
        flight_id=flight.id,
        seat_count=data.seat_count,
        total_price=total_price,
        coupon_id=coupon.id if coupon else None,
        request_ip=request.client.host if request.client else None,
        device_id=data.device_id,
        user_agent=request.headers.get("user-agent")
    )
    session.add(reservation)
    session.commit()
    session.refresh(reservation)

    return reservation


# 예약 조회
@router.get("/reservations/{reservation_id}")
def get_reservation(
    reservation_id: int,
    session: Session = Depends(get_session)
):

    reservation = session.get(Reservation, reservation_id)

    if not reservation:
        raise HTTPException(404, "예약을 찾을 수 없습니다")

    return reservation
