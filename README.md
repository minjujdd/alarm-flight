# alarm-flight
# AI-Based Fraudulent Booking Detection System

## 역할
- A: 프론트엔드·실험 설계
- B: 데이터·AI 모델
- C: 백엔드·DB·Rule Engine

## Branch
- main: 안정 버전
- develop: 통합 개발 버전
- feature/*: 개인 작업 버전

# AI-Based Fraudulent Booking Detection System

## 1. 프로젝트 소개

가상의 저가항공 예약 플랫폼에서 발생하는 사용자 행동을 기록하고,
Rule 기반 탐지와 AI 모델을 이용하여 정상 사용자와 부정 예약 봇을 구분하는 프로젝트입니다.

주요 탐지 대상은 다음과 같습니다.

- 특가 항공권을 자동으로 선점하는 예약 봇
- 여러 계정을 이용한 신규 가입 쿠폰 반복 사용
- 요청 간격과 기기 정보를 변경하는 우회형 봇

실제 항공사나 여행 사이트에는 접근하지 않으며,
팀이 제작한 로컬 모의 예약 플랫폼과 합성 데이터만 사용합니다.

---

## 2. 전체 시스템 흐름

1. 사용자가 항공권을 검색합니다.
2. 항공편을 선택하고 쿠폰을 적용합니다.
3. 예약을 시도합니다.
4. FastAPI 서버가 사용자 행동을 PostgreSQL에 저장합니다.
5. Rule Engine이 Rule Score를 계산합니다.
6. AI 모델이 AI Score를 계산합니다.
7. 두 점수를 결합하여 Risk Score를 계산합니다.
8. Risk Score에 따라 예약 허용, CAPTCHA 또는 예약 제한을 적용합니다.
9. 관리자 화면에서 로그와 탐지 결과를 확인합니다.

---

## 3. 역할 분담

### A: 프론트엔드·실험·결과 통합

- 회원가입·항공권 검색·예약 화면
- 쿠폰·CAPTCHA·차단 화면
- 관리자 대시보드
- 실험 조건 설계
- 결과 그래프 작성
- 보고서와 발표자료 통합

### B: 데이터·Feature·AI 모델

- 정상 사용자 데이터 생성
- 빠른 정상 사용자 데이터 생성
- 단순 봇·우회형 봇 데이터 생성
- Event Log를 Feature로 변환
- Isolation Forest, Random Forest, XGBoost 학습
- 모델 저장 및 성능 분석
- 보고서 데이터·AI 부분 작성

### C: 백엔드·DB·Rule·방어정책

- FastAPI 서버
- PostgreSQL 데이터베이스
- 사용자 행동 로그 저장
- Rule Engine
- AI 모델 API 연동
- Rate Limit과 모의 CAPTCHA
- Rule+AI Hybrid Risk Score
- Docker 실행 환경
- 보고서 시스템 부분 작성

---

## 4. 프로젝트 폴더

```text
project-root/
├── frontend/       # A: 사용자 화면과 관리자 화면
├── backend/        # C: FastAPI, DB, Rule Engine
├── ml/             # B: 데이터 생성, Feature, AI 모델
├── experiments/    # A·B: 반복 실험과 평가 코드
├── data/           # 합성 데이터와 실험 결과
├── docs/           # 회의록, API 명세, ERD, 계획서
├── tests/          # 기능 테스트 코드
├── docker-compose.yml
└── README.md
