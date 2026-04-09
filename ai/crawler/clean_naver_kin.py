import csv
import json
import re

print("데이터 클렌징 + 구조화 시작")

INPUT_FILE = "naver_kin_top1000.csv"
OUTPUT_CSV = "naver_kin_cleaned.csv"
OUTPUT_JSON = "naver_kin_cleaned.json"

# -------------------------------
# 1) 텍스트 정리 함수
# -------------------------------
def clean_text(text):
    if not text:
        return ""

    # 특수문자 정리
    text = re.sub(r"[^\w\s가-힣.,!?]", " ", text)

    # 공백 정리
    text = re.sub(r"\s+", " ", text).strip()

    return text

# -------------------------------
# 2) CSV 읽기
# -------------------------------
rows = []

with open(INPUT_FILE, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f"입력 데이터: {len(rows)}개")

# -------------------------------
# 3) 클렌징 + 구조화
# -------------------------------
cleaned_rows = []

for row in rows:
    keyword = row.get("keyword", "").strip()
    title = clean_text(row.get("title", ""))
    description = clean_text(row.get("description", ""))
    link = row.get("link", "").strip()
    pubdate = row.get("pubDate", "").strip()

    # full_text 생성
    full_text = f"{title} {description}".strip()

    # 길이 계산
    text_length = len(full_text)

    # 너무 짧은 건 제외 (선택)
    if text_length < 20:
        continue

    cleaned_row = {
        "source": "naver_kin",
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

print(f"클렌징 후 데이터: {len(cleaned_rows)}개")

# -------------------------------
# 4) CSV 저장
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
# 5) JSON 저장
# -------------------------------
with open(OUTPUT_JSON, "w", encoding="utf-8-sig") as f:
    json.dump(cleaned_rows, f, ensure_ascii=False, indent=2)

print(f"✅ JSON 저장 완료: {OUTPUT_JSON}")