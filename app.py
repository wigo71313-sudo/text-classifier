"""
文字判別系統 - 網頁版(Streamlit)

本機執行:
    pip install streamlit pytesseract pillow pdfplumber pdf2image
    (系統需另外安裝 tesseract-ocr 與 poppler-utils,見 text_classifier.py 開頭說明)
    streamlit run app.py

部署到雲端(免費):見對話中的「Streamlit Community Cloud 部署步驟」
"""

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


# ============ 判別核心邏輯(與 text_classifier.py 相同) ============

@dataclass
class Rule:
    name: str
    keywords: list = field(default_factory=list)
    patterns: list = field(default_factory=list)
    case_sensitive: bool = False


class TextClassifier:
    def __init__(self):
        self.rules: list[Rule] = []

    def add_rule(self, name, keywords=None, patterns=None, case_sensitive=False):
        self.rules.append(Rule(name=name, keywords=keywords or [], patterns=patterns or [],
                                case_sensitive=case_sensitive))

    def check(self, text: str) -> list[str]:
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


# ============ 預設規則(可在網頁上編輯/新增) ============

DEFAULT_RULES = [
    {"name": "常溫保存", "keywords": "KEEP COOL", "patterns": ""},
    {"name": "冷藏保存", "keywords": "REFRIGERATED",
     "patterns": r"(?<!\d)2\s*[-–~]\s*8(?!\d) | (?<!\d)\+?\s*2\s*°?C?\s*(?:TO|[-–~])\s*\+?\s*8\s*°?C?(?!\d)"},
    {"name": "冷凍保存", "keywords": "KEEP FROZEN", "patterns": ""},
    {"name": "常溫保存_溫度範圍(15-25)", "keywords": "", "patterns": r"(?<!\d)15\s*[-–~]\s*25(?!\d)"},
]


def build_classifier(rules_config: list) -> TextClassifier:
    classifier = TextClassifier()
    for r in rules_config:
        keywords = [k.strip() for k in r["keywords"].split(",") if k.strip()] if r["keywords"] else []
        patterns = [p.strip() for p in r["patterns"].splitlines() if p.strip()] if r["patterns"] else []
        if r["name"] and (keywords or patterns):
            classifier.add_rule(name=r["name"], keywords=keywords, patterns=patterns)
    return classifier


def extract_text_from_image(image_bytes: bytes, lang: str) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(img, lang=lang).strip()


def extract_text_from_pdf(pdf_bytes: bytes, lang: str, use_ocr_fallback=True) -> list:
    """回傳每一頁的文字清單"""
    pages_text = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages_text = [(page.extract_text() or "") for page in pdf.pages]

    if use_ocr_fallback and all(len(t.strip()) == 0 for t in pages_text) and PDF2IMAGE_AVAILABLE and OCR_AVAILABLE:
        images = convert_from_bytes(pdf_bytes, dpi=300)
        pages_text = [pytesseract.image_to_string(img, lang=lang) for img in images]

    return pages_text


# ============ 網頁介面 ============

st.set_page_config(page_title="文字判別系統", page_icon="🔍", layout="wide")
st.title("🔍 文字判別系統")
st.caption("支援純文字 / 圖片 OCR / PDF(含掃描檔),可自訂關鍵字與正規表示式規則")

# ---- 側邊欄:規則設定 ----
with st.sidebar:
    st.header("⚙️ 判別規則設定")
    st.caption("關鍵字用逗號分隔,正規表示式用 | 分隔多個")

    if "rules" not in st.session_state:
        st.session_state.rules = [dict(r) for r in DEFAULT_RULES]

    for i, rule in enumerate(st.session_state.rules):
        with st.expander(f"規則 {i+1}: {rule['name'] or '(未命名)'}", expanded=False):
            rule["name"] = st.text_input("規則名稱", value=rule["name"], key=f"name_{i}")
            rule["keywords"] = st.text_input("關鍵字(逗號分隔)", value=rule["keywords"], key=f"kw_{i}")
            rule["patterns"] = st.text_area("正規表示式(| 分隔)", value=rule["patterns"], key=f"pat_{i}", height=68)
            if st.button("🗑️ 刪除此規則", key=f"del_{i}"):
                st.session_state.rules.pop(i)
                st.rerun()

    if st.button("➕ 新增規則"):
        st.session_state.rules.append({"name": "", "keywords": "", "patterns": ""})
        st.rerun()

    ocr_lang = st.selectbox("OCR 語言", ["chi_tra+chi_sim+eng", "eng", "chi_tra", "chi_sim"], index=0)

classifier = build_classifier(st.session_state.rules)

if not classifier.rules:
    st.warning("目前沒有任何有效規則,請在左側新增至少一條規則。")

# ---- 主畫面:三種輸入方式 ----
tab1, tab2, tab3 = st.tabs(["📝 純文字", "🖼️ 圖片", "📄 PDF"])

with tab1:
    text_input = st.text_area("貼上要判別的文字", height=150, placeholder="例如: KEEP COOL, REFRIGERATED 2-8°C ...")
    if st.button("開始判別", key="btn_text") and text_input.strip():
        matched = classifier.check(text_input)
        if matched:
            st.success(f"✅ 命中規則: {', '.join(matched)}")
        else:
            st.info("❌ 沒有命中任何規則")

with tab2:
    if not OCR_AVAILABLE:
        st.error("此環境缺少 OCR 套件(pytesseract / pillow),圖片判別功能無法使用。")
    else:
        img_file = st.file_uploader("上傳圖片", type=["png", "jpg", "jpeg", "webp"], key="img_upload")
        if img_file:
            st.image(img_file, caption="上傳的圖片", use_container_width=True)
            if st.button("開始判別", key="btn_img"):
                with st.spinner("OCR 辨識中..."):
                    text = extract_text_from_image(img_file.getvalue(), ocr_lang)
                matched = classifier.check(text)
                st.text_area("OCR 讀到的文字", value=text, height=120)
                if matched:
                    st.success(f"✅ 命中規則: {', '.join(matched)}")
                else:
                    st.info("❌ 沒有命中任何規則")

with tab3:
    if not PDF_AVAILABLE:
        st.error("此環境缺少 PDF 套件(pdfplumber),PDF 判別功能無法使用。")
    else:
        pdf_file = st.file_uploader("上傳 PDF(支援多頁,含掃描檔)", type=["pdf"], key="pdf_upload")
        group_pattern = st.text_input(
            "文件分組正規表示式(選填)",
            placeholder=r"例如 160-\d{8},用來把橫跨多頁的同一份文件合併後再判別",
        )
        if pdf_file and st.button("開始判別", key="btn_pdf"):
            with st.spinner("讀取 PDF 中(掃描檔會需要較長時間進行 OCR)..."):
                pages_text = extract_text_from_pdf(pdf_file.getvalue(), ocr_lang)

            results = {}
            if group_pattern:
                for text in pages_text:
                    m = re.search(group_pattern, text)
                    doc_id = m.group(0) if m else f"未識別頁面_{len(results)}"
                    results[doc_id] = results.get(doc_id, "") + "\n" + text
            else:
                for i, text in enumerate(pages_text, 1):
                    results[f"第{i}頁"] = text

            st.write(f"共辨識出 **{len(results)}** 份文件")

            matched_any = False
            for doc_id, text in results.items():
                matched = classifier.check(text)
                if matched:
                    matched_any = True
                    with st.expander(f"✅ {doc_id} -> {', '.join(matched)}"):
                        st.text_area("文字內容", value=text.strip(), height=150, key=f"pdf_text_{doc_id}")

            if not matched_any:
                st.info("❌ 沒有任何文件命中規則")
