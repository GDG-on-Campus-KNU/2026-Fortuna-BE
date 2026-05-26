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

# 2. Git pre-commit hook 등록 (커밋 시 코드 포맷터/린터 자동 검증용)
uv run pre-commit install

# 3. 어플리케이션 실행
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

- Health: http://localhost:8000/health
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

1. `POST /api/v1/auth/signup`
2. `POST /api/v1/auth/login`
3. `POST /uploads`
4. `POST /jobs`
5. `GET /jobs/{job_id}`

`/jobs`는 현재 파일 업로드와 job metadata 생성을 수행하며, job은 `pending / queued` 상태로 생성됩니다. 대본 생성, TTS, 최종 콘텐츠 생성 worker는 아직 API 흐름에 연결되어 있지 않습니다.

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
