"""
꿀템장바구니 - 자막 추출기
유튜브 영상에서 자막(스크립트)을 추출합니다.
(youtube-transcript-api 0.7+ 버전 대응)
"""
from typing import Optional, List, TypedDict
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


class TranscriptItem(TypedDict):
    """자막 항목 타입"""
    text: str
    start: float
    duration: float


class TranscriptResult(TypedDict):
    """자막 추출 결과 타입"""
    video_id: str
    language: str
    transcript: List[TranscriptItem]
    full_text: str


class TranscriptExtractor:
    """유튜브 자막 추출기"""

    def __init__(self) -> None:
        self.preferred_languages: List[str] = ["ko", "en"]
        self.api: YouTubeTranscriptApi = YouTubeTranscriptApi()

    def get_transcript(self, video_id: str) -> Optional[TranscriptResult]:
        """
        영상 자막 추출

        Returns:
            {
                "video_id": str,
                "language": str,
                "transcript": [{"text": str, "start": float, "duration": float}, ...],
                "full_text": str
            }
        """
        try:
            # 자막 목록 조회
            transcript_list = self.api.list(video_id)

            transcript_data = None
            language = None

            # 한국어 자막 우선 시도
            for t in transcript_list:
                if t.language_code in self.preferred_languages:
                    transcript_data = t.fetch()
                    language = t.language_code
                    if not t.is_generated:
                        language += " (manual)"
                    else:
                        language += " (auto)"
                    break

            # 선호 언어가 없으면 첫 번째 자막 사용
            if transcript_data is None:
                try:
                    first = next(iter(transcript_list))
                    transcript_data = first.fetch()
                    language = first.language_code
                except StopIteration:
                    return None

            if transcript_data is None:
                return None

            # 전체 텍스트 결합
            full_text = " ".join([item.text for item in transcript_data])

            # Snippet 객체를 딕셔너리로 변환
            transcript_dicts = [
                {"text": item.text, "start": item.start, "duration": item.duration}
                for item in transcript_data
            ]

            return {
                "video_id": video_id,
                "language": language,
                "transcript": transcript_dicts,
                "full_text": full_text,
            }

        except TranscriptsDisabled:
            return None
        except NoTranscriptFound:
            return None
        except Exception as e:
            error_msg = str(e).lower()
            if "disabled" not in error_msg and "unavailable" not in error_msg:
                print(f"  [!] 자막 추출 오류 ({video_id}): {e}")
            return None

    def get_transcript_with_timestamps(self, video_id: str) -> Optional[str]:
        """타임스탬프가 포함된 자막 텍스트 반환"""
        result = self.get_transcript(video_id)
        if not result:
            return None

        lines = []
        for item in result["transcript"]:
            timestamp = self._format_timestamp(item["start"])
            text = item["text"].strip()
            if text:
                lines.append(f"[{timestamp}] {text}")

        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """초를 MM:SS 형식으로 변환"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"


def main():
    """테스트 실행"""
    extractor = TranscriptExtractor()
    test_video_id = "dQw4w9WgXcQ"

    print(f"영상 자막 추출 테스트: {test_video_id}")
    result = extractor.get_transcript(test_video_id)

    if result:
        print(f"\n언어: {result['language']}")
        print(f"자막 수: {len(result['transcript'])}개")
        print(f"\n전체 텍스트 (앞 300자):")
        print(result["full_text"][:300])
    else:
        print("자막을 가져올 수 없습니다.")


if __name__ == "__main__":
    main()
