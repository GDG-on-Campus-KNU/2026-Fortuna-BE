# Fortuna Backend API

FastAPI 기반 백엔드입니다. 현재 구현된 주요 범위는 인증, 파일 업로드, GCS 저장, PostgreSQL metadata 저장, job 접수입니다.

## Stack

- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- Google Cloud Storage
- Gemini / Google Cloud TTS 연동 준비
- uv
- Docker Compose

## Environment Files

실제 실행 파일은 직접 만들고, 예시 파일만 git에 올립니다.

- Local Python 실행: `.env.example`을 복사해 `.env` 생성
- Docker Compose 실행: `.env.docker.example`을 복사해 `.env.docker` 생성

```bash
cp .env.example .env
cp .env.docker.example .env.docker
```

다음 파일은 절대 git에 올리지 않습니다.

- `.env`
- `.env.docker`
- `.gcs-key.json`

## Local Run

`.env`에서 필요한 값을 채웁니다.

```env
DATABASE_URL=postgresql://fortuna_user:change_me@localhost:5432/fortuna
JWT_SECRET_KEY=replace-with-a-generated-secret
GEMINI_API_KEY=
STORAGE_BACKEND=local
METADATA_BACKEND=json
```

GCS를 로컬 Python 실행에서 사용할 때:

```env
STORAGE_BACKEND=gcs
GCS_BUCKET_NAME=replace-with-your-gcs-bucket
GOOGLE_APPLICATION_CREDENTIALS=./.gcs-key.json
```

실행:

```bash
uv sync
uv run main.py
```

## Docker Compose Run

`.env.docker`에서 필요한 값을 채웁니다.

```env
JWT_SECRET_KEY=replace-with-a-generated-secret
STORAGE_BACKEND=gcs
GCS_BUCKET_NAME=replace-with-your-gcs-bucket
GCS_KEY_FILE=./.gcs-key.json
COMPOSE_METADATA_BACKEND=postgres
```

실행:

```bash
docker compose --env-file .env.docker up --build
```

확인:

```bash
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker exec postgres pg_isready -U postgres -d fortuna
docker compose --env-file .env.docker exec postgres psql -U postgres -d fortuna -c "\dt"
```

API:

- Health: http://localhost:8000/api/v1/health
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

중지:

```bash
docker compose --env-file .env.docker down
```

PostgreSQL volume까지 삭제:

```bash
docker compose --env-file .env.docker down -v
```

## API Flow

현재 가능한 흐름:

1. `POST /api/v1/auth/signup` (회원가입)
2. `POST /api/v1/auth/login` (로그인)
3. `POST /api/v1/notebooks` (노트북 생성)
4. `POST /api/v1/notebooks/{notebook_id}/sources` (노트북에 소스 파일 업로드)
5. `POST /api/v1/jobs` (팟캐스트 생성 백그라운드 작업 접수)
6. `GET /api/v1/jobs/{job_id}` (작업 상태 및 진행도 조회)
7. `GET /api/v1/notebooks/{notebook_id}` (노트북 정보 및 연동된 팟캐스트/소스 리스트 조회)
8. `GET /api/v1/podcasts` (전체 생성 완료된 팟캐스트 목록 조회)

## GCS

GCS storage는 private bucket 기준입니다.

- 원본 파일: `uploads/{user_id}/{file_id}/original.ext`
- 추출 텍스트: `uploads/{user_id}/{file_id}/extracted.txt`
- 스크립트 파일: `scripts/{user_id}/{script_id}.json`
- 오디오 파일: `audio/{user_id}/{audio_id}.wav|mp3`

오디오 URL은 signed URL로 발급됩니다. 만료 시간은 다음 변수로 조정합니다.

```env
GCS_SIGNED_URL_EXPIRATION_MINUTES=60
```

## Tests

기본 테스트:

```bash
uv run python -m pytest -q
```

실제 PostgreSQL 통합 테스트:

```bash
POSTGRES_TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fortuna \
uv run python -m pytest tests/test_postgres_integration.py -q
```

PowerShell:

```powershell
$env:POSTGRES_TEST_DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/fortuna'
uv run python -m pytest tests/test_postgres_integration.py -q
```

## Cloud Run 배포

`scripts/deploy.sh`로 로컬에서 Google Cloud Run에 배포합니다.

### 사전 조건

```bash
# gcloud 로그인 및 프로젝트 설정
gcloud auth login
gcloud config set project studycast-46901

# Docker 인증 (처음 한 번만)
gcloud auth configure-docker asia-northeast3-docker.pkg.dev
```

### 실행

```bash
# 빌드 + Push + 배포 (일반 배포)
./scripts/deploy.sh

# 이미지 빌드·Push만 (배포 제외)
./scripts/deploy.sh --build-only

# 빌드 없이 현재 latest 이미지로 재배포
./scripts/deploy.sh --no-build
```

### 배포 흐름

1. `docker build` — 이미지 빌드 (`GIT_COMMIT` 태그 포함)
2. `docker push` — Artifact Registry에 Push (`asia-northeast3-docker.pkg.dev/studycast-46901/cloud-run-source-deploy/studycast-be:<sha>`)
3. `gcloud run deploy` — Cloud Run 새 리비전 배포
4. `/api/v1/health` 폴링으로 배포 완료 자동 확인

