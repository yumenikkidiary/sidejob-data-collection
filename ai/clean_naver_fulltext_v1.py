import csv
import re

print("full text 클렌징 시작")

INPUT_FILE = "naver_kin_full_raw_v1.csv"
OUTPUT_FILE = "naver_kin_full_cleaned_v1.csv"

rows = []

with open(INPUT_FILE, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f"입력 데이터 수: {len(rows)}개")

# -------------------------------
# 1) 질문 본문만 자르기
# -------------------------------
def extract_question_only(text):
    if not text:
        return ""

    # 답변 시작 지점 기준으로 자르기
    split_keywords = [
        "답변",
        "채택",
        "전문가 답변"
    ]

    for keyword in split_keywords:
        if keyword in text:
            text = text.split(keyword)[0]

    return text.strip()

# -------------------------------
# 2) 메타 제거
# -------------------------------
def clean_text(text):
    if not text:
        return ""

    # 조회수/작성일 제거
    text = re.sub(r"조회수\s*\d+", "", text)
    text = re.sub(r"작성일\s*\d{4}\.\d{2}\.\d{2}", "", text)

    # 불필요 문구 제거
    remove_words = [
        "질문",
        "내공",
        "비공개",
        "댓글",
        "나도 궁금해요",
        "메뉴 더보기",
        "새 창"
    ]

    for word in remove_words:
        text = text.replace(word, "")

    # 공백 정리
    text = re.sub(r"\s+", " ", text).strip()

    return text

# -------------------------------
# 3) 실행
# -------------------------------
cleaned_rows = []

for row in rows:
    full_text = row.get("full_question_text", "")

    # 질문만 추출
    question_text = extract_question_only(full_text)

    # 정리
    question_text = clean_text(question_text)

    if len(question_text) < 50:
        continue

    new_row = {
        "source": row.get("source"),
        "title": row.get("title"),
        "question_text": question_text,
        "link": row.get("link")
    }

    cleaned_rows.append(new_row)

print(f"정제 후 데이터 수: {len(cleaned_rows)}개")

# -------------------------------
# 4) 저장
# -------------------------------
with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["source", "title", "question_text", "link"])
    writer.writeheader()
    writer.writerows(cleaned_rows)

print(f"✅ 저장 완료: {OUTPUT_FILE}")