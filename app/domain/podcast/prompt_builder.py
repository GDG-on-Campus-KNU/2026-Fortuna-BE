from app.domain.podcast.schemas import DetailLevel, DurationMinutes, ScriptFormat


class PromptBuilder:
    def build(
        self,
        source_text: str,
        duration_minutes: DurationMinutes,
        script_format: ScriptFormat,
        detail_level: DetailLevel,
    ) -> str:
        format_instruction = {
            "summary": (
                "자료의 핵심 개념을 학습자가 이해하기 쉬운 요약형 팟캐스트 대본으로 작성한다. "
                "한 명의 진행자가 자연스럽게 설명하는 내레이션 형식을 사용한다."
            ),
        }[script_format]
        detail_instruction = {
            "brief": "핵심 개념만 간결하게 설명한다.",
            "normal": "핵심 개념과 예시를 균형 있게 설명한다.",
            "detailed": "배경, 핵심 개념, 예시, 오해하기 쉬운 지점을 자세히 설명한다.",
        }[detail_level]

        return (
            "너는 한국어 학습형 팟캐스트 작가다.\n"
            f"아래 학습 자료를 바탕으로 {duration_minutes}분 분량의 한국어 팟캐스트 대본을 작성하라.\n\n"
            "작성 조건:\n"
            "- 언어는 한국어로 고정한다.\n"
            "- 전문 용어, 고유명사, 기술명, 인명, 제품명은 무리하게 번역하지 말고 원문을 유지한다.\n"
            "- 학습자가 들으면서 이해하기 쉽게 문장은 구어체로 작성한다.\n"
            "- 자료에 없는 사실은 추정하지 않는다.\n"
            "- 전체 흐름은 도입, 핵심 요약, 정리 순서로 구성한다.\n"
            f"- {format_instruction}\n"
            f"- {detail_instruction}\n"
            "- 오디오 변환에 적합하도록 마크다운 표, 복잡한 목록, 이미지는 사용하지 않는다.\n\n"
            f'학습 자료:\n"""\n{source_text}\n"""\n'
        )
