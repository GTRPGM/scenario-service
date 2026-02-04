import re
from typing import Dict


class KoreanCleaner:
    """
    Utility for normalizing Korean text, handling English transliteration and numbers.
    Useful for cleaning LLM generated scenario text or preparing for TTS.
    """

    ENGLISH_TO_KOREAN: Dict[str, str] = {
        "a": "에이",
        "b": "비",
        "c": "씨",
        "d": "디",
        "e": "이",
        "f": "에프",
        "g": "쥐",
        "h": "에이치",
        "i": "아이",
        "j": "제이",
        "k": "케이",
        "l": "엘",
        "m": "엠",
        "n": "엔",
        "o": "오",
        "p": "피",
        "q": "큐",
        "r": "알",
        "s": "에스",
        "t": "티",
        "u": "유",
        "v": "브이",
        "w": "더블유",
        "x": "엑스",
        "y": "와이",
        "z": "제트",
    }

    NUMBER_TO_KOREAN: Dict[str, str] = {
        "0": "영",
        "1": "일",
        "2": "이",
        "3": "삼",
        "4": "사",
        "5": "오",
        "6": "육",
        "7": "칠",
        "8": "팔",
        "9": "구",
    }

    def normalize_text(self, text: str) -> str:
        text = self._normalize_numbers(text)
        text = self._normalize_english_text(text)
        return text

    def _normalize_numbers(self, text: str) -> str:
        for num, kor in self.NUMBER_TO_KOREAN.items():
            text = text.replace(num, kor)
        return text

    def _normalize_english_text(self, text: str) -> str:
        def replace_match(match: re.Match) -> str:
            char = match.group(0).lower()
            return self.ENGLISH_TO_KOREAN.get(char, char)

        return re.sub(r"[a-zA-Z]", replace_match, text)
