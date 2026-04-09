import csv

print("지식iN 최종 1000개 선별 시작")

STRICT_FILE = "naver_kin_story_strict.csv"
REVIEW_FILE = "naver_kin_story_review.csv"
OUTPUT_FILE = "naver_kin_top1000.csv"

TARGET_COUNT = 1000

# -------------------------------
# 1) CSV 읽기
# -------------------------------
def read_csv(filename):
    rows = []
    with open(filename, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

strict_rows = read_csv(STRICT_FILE)
review_rows = read_csv(REVIEW_FILE)

print(f"strict 파일 수: {len(strict_rows)}개")
print(f"review 파일 수: {len(review_rows)}개")

# -------------------------------
# 2) 보조 점수 계산
# -------------------------------
FIRST_PERSON_PATTERNS = [
    "저는", "제가", "저도", "제 경우", "제 경험", "직접",
    "내가", "저의", "저한테"
]

STORY_PATTERNS = [
    "처음", "시작", "시작했", "해봤", "했다가", "했는데",
    "그러다가", "근데", "결국", "그래서", "이후", "하다가",
    "알게 됐", "접었", "그만뒀", "포기했", "망했", "망했다"
]

LOSS_PATTERNS = [
    "손해", "손실", "적자", "돈만 날", "시간만 날", "후회",
    "사기", "속았", "매출이 안", "수익이 안", "0원", "문을 닫",
    "철수", "안 벌", "안 팔", "적자남", "접었다"
]

QUESTION_PATTERNS = [
    "인가요", "일까요", "할까요", "되나요", "가능한가요", "어떤가요",
    "괜찮나요", "맞나요", "추천", "추천 좀", "해본 사람", "아는 사람",
    "궁금", "질문", "알려주세요", "도와주세요", "후기 있나요"
]

NUMERIC_PATTERNS = [
    "만원", "천원", "원", "개월", "달", "주", "일", "%", "년"
]

def count_hits(text, keywords):
    return sum(1 for k in keywords if k in text)

def calc_bonus_score(text):
    bonus = 0
    bonus += count_hits(text, FIRST_PERSON_PATTERNS) * 3
    bonus += count_hits(text, STORY_PATTERNS) * 3
    bonus += count_hits(text, LOSS_PATTERNS) * 4
    bonus += count_hits(text, NUMERIC_PATTERNS) * 1
    bonus -= count_hits(text, QUESTION_PATTERNS) * 3
    return bonus

# -------------------------------
# 3) 정렬용 최종 점수 계산
# -------------------------------
def safe_int(value):
    try:
        return int(float(value))
    except:
        return 0

def enrich_rows(rows, source_name):
    enriched = []

    for row in rows:
        title = row.get("title", "").strip()
        description = row.get("description", "").strip()
        text = f"{title}\n{description}"

        question_score = safe_int(row.get("question_score", 0))
        experience_score = safe_int(row.get("experience_score", 0))
        success_score = safe_int(row.get("success_score", 0))
        final_score = safe_int(row.get("final_score", 0))

        bonus_score = calc_bonus_score(text)

        # strict 파일은 기본 가산점
        source_bonus = 5 if source_name == "strict" else 0

        ranking_score = final_score + bonus_score + source_bonus

        new_row = {
            "source": source_name,
            "keyword": row.get("keyword", "").strip(),
            "title": title,
            "description": description,
            "link": row.get("link", "").strip(),
            "pubDate": row.get("pubDate", "").strip(),
            "question_score": question_score,
            "experience_score": experience_score,
            "success_score": success_score,
            "final_score": final_score,
            "bonus_score": bonus_score,
            "ranking_score": ranking_score,
            "reason": row.get("reason", "").strip()
        }

        enriched.append(new_row)

    return enriched

strict_enriched = enrich_rows(strict_rows, "strict")
review_enriched = enrich_rows(review_rows, "review")

# -------------------------------
# 4) 정렬
# -------------------------------
strict_sorted = sorted(
    strict_enriched,
    key=lambda x: (
        x["ranking_score"],
        x["experience_score"],
        -x["question_score"]
    ),
    reverse=True
)

review_sorted = sorted(
    review_enriched,
    key=lambda x: (
        x["ranking_score"],
        x["experience_score"],
        -x["question_score"]
    ),
    reverse=True
)

# -------------------------------
# 5) strict 우선 + review 보충
# -------------------------------
selected = []
seen_links = set()

for row in strict_sorted:
    link = row["link"]
    if link and link not in seen_links:
        selected.append(row)
        seen_links.add(link)
    if len(selected) >= TARGET_COUNT:
        break

if len(selected) < TARGET_COUNT:
    for row in review_sorted:
        link = row["link"]
        if link and link not in seen_links:
            selected.append(row)
            seen_links.add(link)
        if len(selected) >= TARGET_COUNT:
            break

print(f"최종 선별 수: {len(selected)}개")

# -------------------------------
# 6) 저장
# -------------------------------
fieldnames = [
    "source", "keyword", "title", "description", "link", "pubDate",
    "question_score", "experience_score", "success_score",
    "final_score", "bonus_score", "ranking_score", "reason"
]

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(selected)

print(f"✅ 저장 완료: {OUTPUT_FILE}")