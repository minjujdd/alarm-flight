from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


# -------------------------
# 1. DB 테이블
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
# 2. 요청/응답 모델 (DB 테이블 아님)
# -------------------------

class SignupRequest(SQLModel):
    email: str
    password: str
    name: str
    phone: Optional[str] = None
    device_id: Optional[str] = None


# 비밀번호 해시를 빼고 돌려주는 회원 정보
class UserPublic(SQLModel):
    id: int
    email: str
    name: str
    phone: Optional[str]
    is_blocked: bool
    created_at: datetime


class SignupResponse(SQLModel):
    user: UserPublic
    coupon: Coupon


class FlightCreate(SQLModel):
    flight_no: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime
    price: int
    total_seats: int
    is_special: bool = False
    sale_open_at: Optional[datetime] = None


class ReservationRequest(SQLModel):
    user_id: int
    flight_id: int
    seat_count: int = 1
    coupon_id: Optional[int] = None
    device_id: Optional[str] = None
