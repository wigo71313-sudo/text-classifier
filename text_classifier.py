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
    case_sensitive: bool = False


class TextClassifier:
    def __init__(self):
        self.rules = []

    def add_rule(self, name, keywords=None, patterns=None, case_sensitive=False):
        self.rules.append(Rule(
            name=name,
            keywords=keywords or [],
            patterns=patterns or [],
            case_sensitive=case_sensitive,
        ))

    def check(self, text):
        matched = []
        for rule in self.rules:
            haystack = text if rule.case_sensitive else text.lower()
            keywords = rule.keywords if rule.case_sensitive else [kw.lower() for kw in rule.keywords]
            if any(kw in haystack for kw in keywords):
                matched.append(rule.name)
                continue
            flags = 0 if rule.case_sensitive else re.IGNORECASE
            if any(re.search(pat, text, flags) for pat in rule.patterns):
                matched.append(rule.name)
        return matched

    def is_match(self, text):
        return len(self.check(text)) > 0

    def extract_text_from_image(self, image_path, lang="chi_tra+chi_sim+eng"):
        if not OCR_AVAILABLE:
            raise RuntimeError("缺少 OCR 套件")
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=lang)
        return text.strip()

    def check_image(self, image_path, lang="chi_tra+chi_sim+eng"):
        text = self.extract_text_from_image(image_path, lang=lang)
        matched = self.check(text)
        return {"text": text, "matched": matched}

    def check_pdf(self, pdf_path, group_pattern=None, ocr_lang="chi_tra+chi_sim+eng"):
        if not PDF_AVAILABLE:
            raise RuntimeError("缺少 PDF 套件")

        with pdfplumber.open(pdf_path) as pdf:
            pages_text = [(page.extract_text() or "") for page in pdf.pages]

        if all(len(t.strip()) == 0 for t in pages_text):
            if not OCR_AVAILABLE:
                raise RuntimeError("這份 PDF 是掃描圖檔,需要 OCR")
            try:
                from pdf2image import convert_from_path
            except ImportError:
                raise RuntimeError("缺少 pdf2image")

            images = convert_from_path(pdf_path, dpi=300)
            pages_text = [pytesseract.image_to_string(img, lang=ocr_lang) for img in images]

        results = {}
        if group_pattern:
            for text in pages_text:
                m = re.search(group_pattern, text)
                doc_id = m.group(0) if m else "未識別頁面_" + str(len(results))
                results[doc_id] = results.get(doc_id, "") + "\n" + text
        else:
            for i, text in enumerate(pages_text, 1):
                results["第" + str(i) + "頁"] = text

        matched_list = []
        for doc_id, text in results.items():
            matched = self.check(text)
            if matched:
                matched_list.append({"id": doc_id, "matched": matched, "text": text})
        return matched_list
