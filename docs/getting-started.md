# Getting Started

이 문서는 Studycast Backend API를 로컬 환경 및 Docker Compose 환경에서 설치, 설정 및 실행하기 위한 가이드입니다.

---

## Makefile Quick Reference (간편 명령어 안내)

프로젝트 루트에 작성된 `Makefile`을 이용해 주요 작업을 간편하게 수행할 수 있습니다.

```bash
# 환경 변수 설정 파일 초기화 (.env, .env.docker 생성)
make init

# 의존성 패키지 설치 및 pre-commit hook 등록
make install

# 로컬 환경에서 FastAPI 서버 실행
make run

# 기본 단위 테스트 실행
make test

# PostgreSQL 연동 통합 테스트 실행
make test-integration

# Docker Compose 빌드 및 백그라운드 실행
make docker-up

# Docker Compose 실행 종료
make docker-down

# Docker Compose 실행 종료 및 볼륨 초기화
make docker-clean

# ruff 포맷팅 실행
make format

# ruff 코드 스타일 린팅 및 자동 수정
make lint

# 각종 빌드 캐시 및 파이썬 임시 파일 정리
make clean
```

---

## Environment Files (환경 변수 설정)

실제 실행 파일은 직접 생성하며, 예시 파일만 Git 버전 관리 시스템에 등록되어 있습니다.

- **Local Python 실행**: `.env.example`을 복사해 `.env` 생성
- **Docker Compose 실행**: `.env.docker.example`을 복사해 `.env.docker` 생성

```bash
cp .env.example .env
cp .env.docker.example .env.docker
```

> [!WARNING]
> 보안 및 설정 충돌 방지를 위해 다음 파일들은 절대 Git에 커밋하거나 공유하지 않습니다:
>
> - `.env`
> - `.env.docker`
> - `.gcs-key.json` (Google Cloud Storage 인증 키 파일)

---

## Local Run (로컬 환경 실행)

### 1. `.env` 파일 설정

생성한 `.env` 파일에 필요한 설정 값을 입력합니다.

```env
DATABASE_URL=postgresql://fortuna_user:change_me@localhost:5432/fortuna
JWT_SECRET_KEY=replace-with-a-generated-secret
GEMINI_API_KEY=
STORAGE_BACKEND=local
METADATA_BACKEND=json
```

**GCS(Google Cloud Storage)를 로컬 Python 실행에서 활성화하는 경우:**

```env
STORAGE_BACKEND=gcs
GCS_BUCKET_NAME=replace-with-your-gcs-bucket
GOOGLE_APPLICATION_CREDENTIALS=./.gcs-key.json
```

### 2. 패키지 설치 및 실행

```bash
# 의존성 패키지 설치 (uv 사용)
uv sync

# Git pre-commit hook 등록 (커밋 시 코드 포맷터/린터 자동 검증용)
uv run pre-commit install

# 어플리케이션 실행
uv run main.py
```

---

## Docker Compose Run (컨테이너 환경 실행)

### 1. `.env.docker` 설정

생성한 `.env.docker` 파일에 필요한 설정 값을 입력합니다.

```env
JWT_SECRET_KEY=replace-with-a-generated-secret
STORAGE_BACKEND=gcs
GCS_BUCKET_NAME=replace-with-your-gcs-bucket
GCS_KEY_FILE=./.gcs-key.json
COMPOSE_METADATA_BACKEND=postgres
```

### 2. 컨테이너 빌드 및 실행

```bash
# 백그라운드에서 빌드 및 컨테이너 실행
docker compose --env-file .env.docker up --build
```

### 3. 정상 동작 및 연동 확인

```bash
# 컨테이너 실행 상태 확인
docker compose --env-file .env.docker ps

# PostgreSQL 데이터베이스 준비 상태 확인
docker compose --env-file .env.docker exec postgres pg_isready -U postgres -d fortuna

# PostgreSQL 테이블 생성 확인
docker compose --env-file .env.docker exec postgres psql -U postgres -d fortuna -c "\dt"
```

### 4. API 엔드포인트 확인

- **Health Check API**: http://localhost:8000/api/v1/health
- **Swagger UI (Interactive API Docs)**: http://localhost:8000/docs
- **ReDoc (Static API Docs)**: http://localhost:8000/redoc

### 5. 서비스 종료

```bash
# 서비스 컨테이너 종료 및 네트워크 리소스 삭제
docker compose --env-file .env.docker down

# PostgreSQL 데이터 볼륨까지 완전히 삭제하려면 다음 명령어 사용 (데이터 유실 주의)
docker compose --env-file .env.docker down -v
```

---

## Tests (테스트 실행 방법)

### 기본 단위 테스트

로컬에서 전체 테스트 스위트를 실행합니다 (상대적으로 가볍고 빠른 테스트 위주).

```bash
uv run python -m pytest -q
```

### PostgreSQL 통합 테스트

실제 PostgreSQL 데이터베이스 인스턴스와 연동하여 통합 테스트를 실행합니다.

**macOS / Linux:**

```bash
POSTGRES_TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fortuna \
uv run python -m pytest tests/test_postgres_integration.py -q
```

**Windows PowerShell:**

```powershell
$env:POSTGRES_TEST_DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/fortuna'
uv run python -m pytest tests/test_postgres_integration.py -q
```
