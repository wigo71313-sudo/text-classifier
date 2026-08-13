import re
import io
import streamlit as st
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

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


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
        self.rules.append(Rule(name=name, keywords=keywords or [], patterns=patterns or [],
                                case_sensitive=case_sensitive))

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


DEFAULT_RULES = [
    {"name": "常溫保存", "keywords": "KEEP COOL", "patterns": ""},
    {"name": "冷藏保存", "keywords": "REFRIGERATED",
