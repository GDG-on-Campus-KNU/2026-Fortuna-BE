# Google Cloud Storage (GCS) Design

이 문서는 Studycast 프로젝트에서 사용하는 Google Cloud Storage(GCS) 버킷 구조 및 관련 파일 경로 설계에 대해 기술합니다.

---

## GCS Bucket Policy

GCS Storage는 **Private Bucket** 기준이며, 비인증 사용자의 무단 접근을 방지합니다. 외부 클라이언트가 직접 파일에 안전하게 임시 접근할 수 있도록 Signed URL을 발급하여 제공합니다.

---

## Folder & File Directory Layout (저장 경로 구조)

버킷 내의 파일 경로는 아래의 명명 규칙(Naming Convention)을 따릅니다.

- **원본 업로드 파일**: `uploads/{user_id}/{file_id}/original.ext`
  - 사용자가 업로드한 원본 파일 (텍스트, PDF 등)
- **추출 텍스트 파일**: `uploads/{user_id}/{file_id}/extracted.txt`
  - 원본 파일에서 텍스트 내용을 추출하여 정제한 파일
- **생성된 스크립트 데이터**: `scripts/{user_id}/{script_id}.json`
  - 팟캐스트 생성을 위해 AI 모델(Gemini)에 의해 정제/변환된 스크립트 JSON 데이터
- **최종 생성 오디오 파일**: `audio/{user_id}/{audio_id}.wav|mp3`
  - Text-to-Speech(TTS) 모듈을 통해 최종 생성된 팟캐스트 오디오 파일

---

## Signed URL Expiration (보안 임시 URL 만료 설정)

오디오 및 원본 파일에 임시 접근할 수 있는 Signed URL의 만료 시간은 환경 변수 설정을 통해 분 단위로 조정할 수 있습니다.

로컬 또는 Docker Compose의 환경 변수 파일(`.env` 혹은 `.env.docker`)에 설정합니다.

```env
# Signed URL 만료 시간 설정 (기본값: 60분)
GCS_SIGNED_URL_EXPIRATION_MINUTES=60
```
