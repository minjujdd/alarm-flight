from datetime import datetime, timedelta
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from database import get_session
from models import (
    Coupon, Reservation, SignupRequest, SignupResponse, User, UserPublic
)


router = APIRouter(tags=["회원"])

SIGNUP_COUPON_DISCOUNT = 10000
SIGNUP_COUPON_DAYS = 30


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, 100_000
    )
    return salt.hex() + ":" + digest.hex()


# 회원가입 (+ 가입 쿠폰 자동 발급)
@router.post("/users/signup", response_model=SignupResponse)
def signup(
    data: SignupRequest,
    request: Request,
    session: Session = Depends(get_session)
):

    exists = session.exec(
        select(User).where(User.email == data.email)
    ).first()

    if exists:
        raise HTTPException(400, "이미 가입된 이메일입니다")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        phone=data.phone,
        signup_ip=request.client.host if request.client else None,
        signup_device_id=data.device_id
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    coupon = Coupon(
        code=secrets.token_hex(6).upper(),
        user_id=user.id,
        coupon_type="signup",
        discount_amount=SIGNUP_COUPON_DISCOUNT,
        expires_at=datetime.now() + timedelta(days=SIGNUP_COUPON_DAYS)
    )
    session.add(coupon)
    session.commit()
    session.refresh(coupon)

    return SignupResponse(
        user=UserPublic.model_validate(user),
        coupon=coupon
    )


# 회원 조회
@router.get("/users/{user_id}", response_model=UserPublic)
def get_user(user_id: int, session: Session = Depends(get_session)):

    user = session.get(User, user_id)

    if not user:
        raise HTTPException(404, "회원을 찾을 수 없습니다")

    return user


# 회원 쿠폰 조회
@router.get("/users/{user_id}/coupons")
def get_user_coupons(user_id: int, session: Session = Depends(get_session)):

    statement = select(Coupon).where(Coupon.user_id == user_id)

    return session.exec(statement).all()


# 회원 예약 조회
@router.get("/users/{user_id}/reservations")
def get_user_reservations(
    user_id: int,
    session: Session = Depends(get_session)
):

    statement = select(Reservation).where(Reservation.user_id == user_id)

    return session.exec(statement).all()
