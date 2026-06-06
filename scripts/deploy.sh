#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Google Cloud Run 배포 스크립트
#
# 사용법:
#   ./scripts/deploy.sh              # 기본 배포 (latest 태그)
#   ./scripts/deploy.sh --build-only # 이미지 빌드·Push만 (배포 제외)
#   ./scripts/deploy.sh --no-build   # 이미지 빌드 없이 현재 latest로 재배포
#
# 필요 조건:
#   - gcloud CLI 인증 완료 (gcloud auth login && gcloud auth configure-docker ...)
#   - Docker Desktop 실행 중
# =============================================================================
set -euo pipefail

# .env 파일이 존재하는 경우 환경 변수 로드
if [ -f .env ]; then
  echo "▶ .env 파일에서 환경 변수 로드 중..."
  while IFS= read -r line || [ -n "$line" ]; do
    line=$(echo "$line" | tr -d '\r')
    if [[ ! "$line" =~ ^# ]] && [[ -n "$line" ]]; then
      if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
        key="${line%%=*}"
        val="${line#*=}"
        val="${val#\"}"
        val="${val%\"}"
        val="${val#\'}"
        val="${val%\'}"
        export "$key"="$val"
      fi
    fi
  done < .env
fi

# ─── 설정 (환경 변수 또는 .env 파일에서 주입 필수) ───────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-${PROJECT_ID:-}}"
REGION="${GCP_REGION:-${REGION:-}}"
SERVICE_NAME="${GCP_SERVICE_NAME:-${SERVICE_NAME:-}}"
AR_REPO="${GCP_AR_REPO:-${AR_REPO:-}}"

if [ -z "${PROJECT_ID}" ] || [ -z "${REGION}" ] || [ -z "${SERVICE_NAME}" ] || [ -z "${AR_REPO}" ]; then
  echo "❌ 오류: 필수 배포 설정 값이 누락되었습니다."
  echo "   로컬 환경 변수나 .env 파일에 다음 값을 정의해 주세요:"
  echo "   - PROJECT_ID (혹은 GCP_PROJECT_ID)"
  echo "   - REGION (혹은 GCP_REGION)"
  echo "   - SERVICE_NAME (혹은 GCP_SERVICE_NAME)"
  echo "   - AR_REPO (혹은 GCP_AR_REPO)"
  exit 1
fi

# 이미지 주소
IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${SERVICE_NAME}"
GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
IMAGE_SHA="${IMAGE_BASE}:${GIT_SHA}"
IMAGE_LATEST="${IMAGE_BASE}:latest"
# ─────────────────────────────────────────────────────────────────────────────



# ─── 플래그 파싱 ─────────────────────────────────────────────────────────────
BUILD=true
DEPLOY=true

for arg in "$@"; do
  case "${arg}" in
    --build-only) DEPLOY=false ;;
    --no-build)   BUILD=false  ;;
    --help|-h)
      sed -n '2,12p' "$0" | sed 's/^# //; s/^#//'
      exit 0
      ;;
    *)
      echo "알 수 없는 옵션: ${arg}"
      echo "사용법: $0 [--build-only|--no-build]"
      exit 1
      ;;
  esac
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Cloud Run 배포 스크립트"
echo "  프로젝트  : ${PROJECT_ID}"
echo "  리전      : ${REGION}"
echo "  서비스    : ${SERVICE_NAME}"
echo "  커밋      : ${GIT_SHA}"
echo "  빌드      : ${BUILD}"
echo "  배포      : ${DEPLOY}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─── Docker 인증 확인 ────────────────────────────────────────────────────────
echo ""
echo "▶ Docker 인증 설정 중..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ─── 빌드 & Push ─────────────────────────────────────────────────────────────
if [ "${BUILD}" = true ]; then
  echo ""
  echo "▶ Docker 이미지 빌드 중..."
  docker build \
    --platform linux/amd64 \
    --build-arg GIT_COMMIT="${GIT_SHA}" \
    -t "${IMAGE_SHA}" \
    -t "${IMAGE_LATEST}" \
    .

  echo ""
  echo "▶ Artifact Registry에 Push 중..."
  docker push "${IMAGE_SHA}"
  docker push "${IMAGE_LATEST}"
  echo "  ✅ Push 완료: ${IMAGE_SHA}"
else
  echo ""
  echo "ℹ️  --no-build: 빌드 건너뜀. 현재 latest 이미지로 배포합니다."
  IMAGE_SHA="${IMAGE_LATEST}"
fi

# ─── Cloud Run 배포 ───────────────────────────────────────────────────────────
if [ "${DEPLOY}" = true ]; then
  echo ""
  echo "▶ Cloud Run에 배포 중..."
  gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE_SHA}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --platform=managed \
    --allow-unauthenticated \
    --quiet

  SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")"

  echo ""
  echo "▶ 배포 검증 중 (/api/v1/health)..."
  deadline=$(( SECONDS + 120 ))
  while [ "${SECONDS}" -lt "${deadline}" ]; do
    body="$(curl -fsS --max-time 8 "${SERVICE_URL}/api/v1/health" 2>/dev/null || true)"
    commit="$(printf '%s' "${body}" | python3 -c \
      'import json,sys; print(json.load(sys.stdin).get("commit",""))' 2>/dev/null || true)"
    echo "  현재 commit = ${commit:-<응답없음>}"
    if [ -n "${commit}" ]; then
      echo ""
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "  ✅ 배포 완료!"
      echo "  URL    : ${SERVICE_URL}"
      echo "  Commit : ${commit}"
      echo "  Docs   : ${SERVICE_URL}/docs"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      exit 0
    fi
    sleep 5
  done

  echo "⚠️  /api/v1/health 응답을 받지 못했습니다. Cloud Run 콘솔에서 상태를 확인하세요."
  echo "  URL: ${SERVICE_URL}"
else
  echo ""
  echo "ℹ️  --build-only: 배포 건너뜀."
  echo "  이미지: ${IMAGE_SHA}"
fi
