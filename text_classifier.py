"""
文字判別程式(支援純文字 + 圖片)

功能:
1. 關鍵字比對(包含判斷)
2. 正規表示式(regex)比對
3. 圖片 OCR:先用 tesseract 把圖片裡的文字讀出來,再套用同一套規則判別

安裝需求(在你自己的電腦上執行前需要先安裝):
    macOS:   brew install tesseract tesseract-lang
    Ubuntu:  sudo apt-get install tesseract-ocr tesseract-ocr-chi-tra tesseract-ocr-chi-sim
    Windows: 到 https://github.com/UB-Mannheim/tesseract/wiki 下載安裝檔,
             安裝時記得勾選 Chinese (Traditional) / Chinese (Simplified) 語言包

    再安裝 Python 套件:
        pip install pytesseract pillow pdfplumber
"""

import re
from dataclasses import dataclass, field

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


@dataclass
class Rule:
    name: str
    keywords: list = field(default_factory=list)
    patterns: list = field(default_factory=list)
    case_sensitive: bool = False  # 英文關鍵字預設不分大小寫,例如 "free" 也會比對到 "FREE"


class TextClassifier:
    def __init__(self):
        self.rules: list[Rule] = []

    def add_rule(self, name: str, keywords: list = None, patterns: list = None,
                 case_sensitive: bool = False):
        """新增一條判別規則。case_sensitive=False
