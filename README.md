# Fortuna Backend API

Fortuna 프로젝트의 백엔드 API 서버입니다.  
이 프로젝트는 **FastAPI**, **SQLAlchemy 2.0 (Async)** 및 **PostgreSQL**을 기반으로 하며, 보안성 높은 사용자 가입, 로그인 및 세션 관리 기능을 지원합니다.

---

## 🛠️ Tech Stack & Security Features

* **Core Framework**: FastAPI
* **Database**: PostgreSQL (asynchronous connection via `asyncpg`)
* **ORM**: SQLAlchemy 2.0 (Modern declarative mapped format)
* **Dependency Manager**: [uv](https://github.com/astral-sh/uv)
* **Security**:
  * **bcrypt**: 일방향 패스워드 해싱 및 솔팅
  * **PyJWT**: 비상태성(stateless) 유저 세션 인증 처리 (Bearer JWT)
  * **UUIDv4 Primary Keys**: 유저 ID 유추 및 데이터 덤프 방지

---

## 🚀 Quick Start & Database Setup

프로젝트 구동에 앞서 데이터베이스 서버 가동 및 환경변수 설정이 필요합니다.

### 1. 데이터베이스(PostgreSQL) 서버 가동하기

#### 옵션 A: Docker를 사용하는 방법 (권장 🐳)
Docker 데몬이 구동 중인 상태에서 아래 명령어를 터미널에 복사해 실행합니다:
```bash
docker run --name fortuna-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=fortuna \
  -p 5432:5432 \
  -d postgres:16-alpine
```

#### 옵션 B: Homebrew 로컬 설치 방식 (macOS 🍺)
Homebrew를 사용하여 컴퓨터에 직접 설치하는 경우 아래 순서대로 수행합니다:
```bash
# 1. PostgreSQL 설치
brew install postgresql@16

# 2. 백그라운드 서비스 실행
brew services start postgresql@16

# 3. 프로젝트용 데이터베이스 생성
createdb fortuna
```

---

### 2. 환경 변수 설정 (`.env`)

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 구동하고자 하는 DB 설정에 맞추어 변수를 작성합니다.

```env
# 1. Docker(옵션 A)를 사용하는 경우의 DATABASE_URL (기본 설정)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fortuna

# 2. Homebrew(옵션 B) 혹은 로컬 직접 설치를 사용하는 경우의 DATABASE_URL
# (계정명 'huigyun-jeong' 자리에 본인의 macOS 유저명을 입력해야 합니다.)
# DATABASE_URL=postgresql+asyncpg://huigyun-jeong@localhost:5432/fortuna

# 보안을 위해 반드시 유니크한 비밀키로 변경해주세요. (openssl rand -hex 32 등으로 생성 가능)
JWT_SECRET_KEY=94c16a1c8651079541a774dbba22cb33be8ebc7f9994c65e8a5b29381c8ee90d
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

### 3. 패키지 설치 및 실행

프로젝트는 패키지 관리자로 `uv`를 사용합니다.

```bash
# 1. 의존성 설치
uv sync

# 2. 어플리케이션 실행
uv run main.py
```
> **팁**: 어플리케이션이 처음 구동될 때, 데이터베이스에 필요한 테이블(`users` 테이블 등)이 없는 경우 자동으로 자동 생성(`lifespan` 이벤트)되므로 별도의 DDL 스크립트를 수동 실행할 필요가 없습니다.

---

## 🔍 API 테스트 및 문서 확인 (Swagger)

서버가 켜진 상태에서 아래 링크로 접속하시면 대화형 API 명세서를 확인할 수 있으며 즉석에서 회원가입 및 토큰 발급 테스트가 가능합니다.

* **API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📁 Project Structure

```text
app/
├── api/          # API 컨트롤러 및 라우터 정의
│   ├── auth.py   # 회원가입, 로그인, 내 정보 조회 라우트
│   └── router.py # 엔드포인트 통합 및 버저닝(v1)
├── core/         # 어플리케이션 설정, 보안, DB 엔진 구성
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/       # SQLAlchemy 데이터베이스 스키마 모델 정의
│   └── user.py
├── repositories/ # 데이터베이스 직접 연동(DAO) 레이어
│   └── user_repository.py
├── schemas/      # Pydantic 데이터 포맷 정의 및 유효성 검증
│   └── user.py
└── services/     # 비즈니스 로직 및 워크플로우 처리
    └── auth_service.py
```