from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import hashlib
import random
import secrets

from fastapi import FastAPI, HTTPException, Request
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
# 1-1. 요청/응답 모델 (DB 테이블 아님)
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


# -------------------------
# 12. 비밀번호 해시
# -------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, 100_000
    )
    return salt.hex() + ":" + digest.hex()


# -------------------------
# 13. 회원가입 (+ 가입 쿠폰 자동 발급)
# -------------------------

SIGNUP_COUPON_DISCOUNT = 10000
SIGNUP_COUPON_DAYS = 30


@app.post("/users/signup", response_model=SignupResponse)
def signup(data: SignupRequest, request: Request):

    with Session(engine) as session:
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


# -------------------------
# 14. 회원 조회
# -------------------------

@app.get("/users/{user_id}", response_model=UserPublic)
def get_user(user_id: int):

    with Session(engine) as session:
        user = session.get(User, user_id)

        if not user:
            raise HTTPException(404, "회원을 찾을 수 없습니다")

        return user


# -------------------------
# 15. 회원 쿠폰 조회
# -------------------------

@app.get("/users/{user_id}/coupons")
def get_user_coupons(user_id: int):

    with Session(engine) as session:
        statement = select(Coupon).where(
            Coupon.user_id == user_id
        )

        return session.exec(statement).all()


# -------------------------
# 16. 회원 예약 조회
# -------------------------

@app.get("/users/{user_id}/reservations")
def get_user_reservations(user_id: int):

    with Session(engine) as session:
        statement = select(Reservation).where(
            Reservation.user_id == user_id
        )

        return session.exec(statement).all()


# -------------------------
# 17. 항공편 등록 (관리자·테스트용)
# -------------------------

@app.post("/flights")
def create_flight(data: FlightCreate):

    flight = Flight(
        **data.model_dump(),
        remaining_seats=data.total_seats
    )

    with Session(engine) as session:
        session.add(flight)
        session.commit()
        session.refresh(flight)

        return flight


# -------------------------
# 18. 항공편 검색
# -------------------------

@app.get("/flights")
def search_flights(
    departure_airport: Optional[str] = None,
    arrival_airport: Optional[str] = None,
    special_only: bool = False
):

    with Session(engine) as session:
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


# -------------------------
# 19. 항공편 상세 조회
# -------------------------

@app.get("/flights/{flight_id}")
def get_flight(flight_id: int):

    with Session(engine) as session:
        flight = session.get(Flight, flight_id)

        if not flight:
            raise HTTPException(404, "항공편을 찾을 수 없습니다")

        return flight


# -------------------------
# 20. 예약 (+ 쿠폰 사용)
# -------------------------

@app.post("/reservations")
def create_reservation(data: ReservationRequest, request: Request):

    now = datetime.now()

    with Session(engine) as session:
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


# -------------------------
# 21. 예약 조회
# -------------------------

@app.get("/reservations/{reservation_id}")
def get_reservation(reservation_id: int):

    with Session(engine) as session:
        reservation = session.get(Reservation, reservation_id)

        if not reservation:
            raise HTTPException(404, "예약을 찾을 수 없습니다")

        return reservation
