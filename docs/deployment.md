# Cloud Run Deployment Guide

이 문서는 `scripts/deploy.sh` 스크립트를 사용하여 로컬 환경에서 Google Cloud Run에 Studycast Backend API 서비스를 빌드하고 배포하는 절차를 설명합니다.

---

## Prerequisites (사전 조건)

배포 스크립트를 실행하기 전에 Google Cloud SDK(gcloud CLI) 및 Docker가 설치되어 있어야 하며 아래의 초기 설정이 완료되어 있어야 합니다.

### 1. gcloud CLI 인증 및 프로젝트 설정

```bash
# Google 계정 로그인 인증
gcloud auth login

# 배포할 Google Cloud 프로젝트 ID 설정
gcloud config set project <your-gcp-project-id>
```

### 2. Artifact Registry Docker 인증 (최초 1회 실행)

Google Cloud Artifact Registry에 Docker 이미지를 Push할 수 있도록 도커 자격증명을 설정합니다.

```bash
gcloud auth configure-docker asia-northeast3-docker.pkg.dev
```

---

## Deployment Commands (배포 명령어)

프로젝트 루트 폴더 내의 `scripts/deploy.sh` 스크립트를 사용하여 배포를 수행합니다.

### 1. 일반 배포 (빌드 + Push + 배포)

가장 보편적인 방법으로, 이미지를 빌드한 뒤 Registry에 업로드하고 Cloud Run에 새 버전을 적용합니다.

```bash
./scripts/deploy.sh
```

### 2. Docker 이미지 빌드 및 Push만 수행 (배포 제외)

Cloud Run 배포를 보류하고 원격 컨테이너 레지스트리에 빌드된 최신 이미지만 보관할 경우 사용합니다.

```bash
./scripts/deploy.sh --build-only
```

### 3. 빌드 없이 최신 이미지로 재배포

추가 빌드 없이 이미 Artifact Registry에 업로드된 `latest` 이미지를 기반으로 서비스 리비전만 다시 배포할 경우 사용합니다.

```bash
./scripts/deploy.sh --no-build
```

---

## Deployment Flow (배포 상세 흐름)

`deploy.sh` 스크립트 실행 시 내부적으로 수행되는 프로세스는 다음과 같습니다.

1. **`docker build`**: 현재 코드를 기반으로 Docker 컨테이너 이미지를 빌드합니다. (이때 빌드 태그는 Git의 최신 커밋 해시인 `GIT_COMMIT`을 포함합니다.)
2. **`docker push`**: 빌드된 이미지를 원격 구글 아티팩트 레지스트리(`asia-northeast3-docker.pkg.dev/<your-gcp-project-id>/cloud-run-source-deploy/studycast-be:<sha>`)에 업로드합니다.
3. **`gcloud run deploy`**: Cloud Run에 신규 리비전 배포 명령을 전송하여 컨테이너 인스턴스를 업데이트합니다.
4. **Health Check Polling**: 배포 완료 직후 `/api/v1/health` 엔드포인트를 주기적으로 호출(Polling)하여 신규 배포 버전이 정상 서비스 가능한 상태인지 최종 자동 확인합니다.
