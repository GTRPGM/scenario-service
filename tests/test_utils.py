from scenario.core.utils.text import KoreanCleaner


def test_korean_cleaner_normalization():
    cleaner = KoreanCleaner()

    # Test number normalization
    assert cleaner.normalize_text("123") == "일이삼"

    # Test English transliteration
    assert cleaner.normalize_text("abc") == "에이비씨"

    # Test mixed content
    assert cleaner.normalize_text("Lv.10 용사") == "엘브이.일영 용사"

    # Test case insensitivity
    assert cleaner.normalize_text("FastAPI") == "에프에이에스티에이피아이"
