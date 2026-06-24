# API Reference & Flow

이 문서는 Studycast Backend API의 주요 엔드포인트와 API 호출 흐름(API Flow)을 설명합니다.

---

## API Docs & Health Check

서비스 실행 후 웹 브라우저를 통해 다음 엔드포인트에서 API 사양을 확인하고 테스트할 수 있습니다.

- **Interactive API Docs (Swagger UI)**: http://localhost:8000/docs
- **Static API Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check API**: http://localhost:8000/api/v1/health

---

## API Flow (기본 시나리오 흐름)

FastAPI 서버가 제공하는 주요 API 기능의 호출 순서와 사용 흐름은 다음과 같습니다.

### 1. 인증 및 회원 관리

서비스 이용을 위해 계정을 생성하고 토큰을 발급받습니다.

1. **회원가입**: `POST /api/v1/auth/signup`
   - 사용자 계정을 생성합니다.
2. **로그인**: `POST /api/v1/auth/login`
   - 계정 인증을 완료하고 JWT Access Token을 발급받습니다. 이후의 모든 API 호출에는 Authorization 헤더에 Bearer 토큰을 포함해야 합니다.

### 2. 노트북 및 소스 파일 관리

팟캐스트 제작의 기본 단위인 노트북을 생성하고, 참고할 소스 파일을 업로드합니다.

3. **노트북 생성**: `POST /api/v1/notebooks`
   - 새로운 작업 공간(노트북)을 생성합니다.
4. **소스 파일 업로드**: `POST /api/v1/notebooks/{notebook_id}/sources`
   - 특정 노트북에 팟캐스트 리소스가 될 텍스트, 문서 등의 소스 파일을 업로드합니다. 업로드된 파일은 GCS에 저장되고 메타데이터가 PostgreSQL에 기록됩니다.

### 3. 팟캐스트 생성 작업 요청 및 상태 조회

업로드된 소스들을 바탕으로 AI 기반 팟캐스트 오디오 파일을 생성하는 백그라운드 작업을 실행합니다.

5. **작업 요청 (Job Submit)**: `POST /api/v1/jobs`
   - 팟캐스트 오디오 생성을 위한 백그라운드 작업(Job)을 요청합니다.
6. **작업 상태 조회**: `GET /api/v1/jobs/{job_id}`
   - 백그라운드 작업의 진행도(Progress) 및 처리 상태(Status: PENDING, RUNNING, COMPLETED, FAILED)를 조회합니다.

### 4. 결과물 및 목록 조회

생성된 노트북 정보와 완료된 팟캐스트 목록을 조회합니다.

7. **노트북 상세 조회**: `GET /api/v1/notebooks/{notebook_id}`
   - 해당 노트북의 상세 정보와 여기에 연동된 팟캐스트 목록 및 소스 파일 리스트를 한 번에 조회합니다.
8. **팟캐스트 목록 조회**: `GET /api/v1/podcasts`
   - 전체 생성 완료된 팟캐스트 결과물 목록을 조회합니다.
