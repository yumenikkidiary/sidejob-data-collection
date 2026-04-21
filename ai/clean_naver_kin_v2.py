import csv
import json
import re

print("지식인 데이터 클렌징 v2 시작")

INPUT_FILE = "naver_kin_top1000.csv"
OUTPUT_CSV = "naver_kin_cleaned_v2.csv"
OUTPUT_JSON = "naver_kin_cleaned_v2.json"

# -------------------------------
# 1) 제거 대상 패턴
# -------------------------------
DATE_PATTERNS = [
    r"\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}",   # 20/03/04 10:16
    r"\d{2}/\d{2}\s+\d{2}:\d{2}",         # 03/04 10:16
    r"\d{2}/\d{2}",                       # 03/04
    r"\d{1,2}분 전",
    r"\d{1,2}시간 전",
    r"\d{1,2}일 전",
    r"방금"
]

REMOVE_PATTERNS = [
    r"\(알수없음\)",
    r"\[알수없음\]",
    r"익명",
    r"공감",
    r"스크랩",
    r"쪽지",
    r"신고"
]

# -------------------------------
# 2) 텍스트 정리 함수
# -------------------------------
def clean_text(text):
    if not text:
        return ""

    text = str(text)

    # 날짜/시간 제거
    for pattern in DATE_PATTERNS:
        text = re.sub(pattern, " ", text)

    # 고정 메타 제거
    for pattern in REMOVE_PATTERNS:
        text = re.sub(pattern, " ", text)

    # 링크 제거
    text = re.sub(r"http[s]?://\S+", " ", text)
    text = re.sub(r"www\.\S+", " ", text)

    # html-like / 깨지는 특수문자 최소 정리
    text = re.sub(r"[^\w\s가-힣.,!?~%/\-]", " ", text)

    # 공백 정리
    text = re.sub(r"\s+", " ", text).strip()

    return text

def normalize_sentence(text):
    if not text:
        return ""

    text = text.strip()

    # 문장부호 앞뒤 공백 정리
    text = re.sub(r"\s+([.,!?])", r"\1", text)
    text = re.sub(r"([.,!?])([가-힣A-Za-z0-9])", r"\1 \2", text)

    # 중복 공백 제거
    text = re.sub(r"\s+", " ", text).strip()

    return text

# -------------------------------
# 3) CSV 읽기
# -------------------------------
rows = []

with open(INPUT_FILE, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f"입력 데이터 수: {len(rows)}개")

# -------------------------------
# 4) 클렌징
# -------------------------------
cleaned_rows = []

for row in rows:
    source = "naver_kin"
    keyword = row.get("keyword", "").strip()

    title_raw = row.get("title", "")
    desc_raw = row.get("description", "")
    link = row.get("link", "").strip()
    pubdate = row.get("pubDate", "").strip()

    title = normalize_sentence(clean_text(title_raw))
    description = normalize_sentence(clean_text(desc_raw))

    # full_text 생성
    full_text = f"{title} {description}".strip()
    full_text = normalize_sentence(full_text)

    text_length = len(full_text)

    # 너무 짧은 건 제거
    if text_length < 30:
        continue

    cleaned_row = {
        "source": source,
        "keyword": keyword,
        "title": title,
        "description": description,
        "full_text": full_text,
        "link": link,
        "pubDate": pubdate,
        "text_length": text_length,
        "label": "unlabeled"
    }

    cleaned_rows.append(cleaned_row)

print(f"클렌징 후 데이터 수: {len(cleaned_rows)}개")

# -------------------------------
# 5) CSV 저장
# -------------------------------
fieldnames = [
    "source",
    "keyword",
    "title",
    "description",
    "full_text",
    "link",
    "pubDate",
    "text_length",
    "label"
]

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(cleaned_rows)

print(f"✅ CSV 저장 완료: {OUTPUT_CSV}")

# -------------------------------
# 6) JSON 저장
# -------------------------------
with open(OUTPUT_JSON, "w", encoding="utf-8-sig") as f:
    json.dump(cleaned_rows, f, ensure_ascii=False, indent=2)

print(f"✅ JSON 저장 완료: {OUTPUT_JSON}")