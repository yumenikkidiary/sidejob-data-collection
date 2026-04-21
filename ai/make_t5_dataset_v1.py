import csv

print("T5 학습용 CSV 생성 시작")

INPUT_FILE = "naver_kin_full_failure_only_v1.csv"
OUTPUT_FILE = "t5_failure_train_v1.csv"

# -------------------------------
# 1) 실패 유형 태그 규칙
# -------------------------------
TAG_RULES = {
    "사기피해": ["사기", "속았다", "사기 당", "먹튀", "원금보장"],
    "초기비용손실": ["초기비용", "가입비", "교육비", "돈만 날", "손실", "손해", "적자"],
    "시장조사부족": ["상품 선정", "시장조사", "재고", "안 팔", "매출이 안"],
    "마케팅부족": ["광고", "노출", "홍보", "유입", "마케팅"],
    "수익모델부족": ["수익이 안", "매출이 안", "수익 구조", "돈이 안", "0원"],
    "운영경험부족": ["처음", "몰랐", "경험이 없", "운영", "관리"],
    "시간부족": ["시간이 없", "직장", "병행", "퇴근 후", "시간 부족"],
    "지속성부족": ["포기", "접었", "그만뒀", "중단", "꾸준히 못"],
    "플랫폼이해부족": ["스마트스토어", "쿠팡파트너스", "블로그", "플랫폼"],
    "과장광고신뢰": ["광고에서", "누구나", "쉽게 번다", "수익보장", "과장"]
}

# -------------------------------
# 2) 실패요인 규칙
# -------------------------------
CAUSE_RULES = [
    ("과장 광고를 믿고 시작함", ["광고", "누구나", "쉽게 번다", "수익보장", "과장"]),
    ("초기 비용이 과도하게 발생함", ["초기비용", "가입비", "교육비", "광고비", "투자금"]),
    ("매출 또는 수익이 발생하지 않음", ["매출이 안", "수익이 안", "0원", "돈이 안"]),
    ("상품/시장 조사 부족", ["상품 선정", "시장조사", "재고", "안 팔"]),
    ("마케팅 역량 부족", ["광고", "홍보", "유입", "노출", "마케팅"]),
    ("운영 경험 부족", ["처음", "경험이 없", "몰랐", "운영", "관리"]),
    ("시간을 꾸준히 투입하지 못함", ["시간이 없", "직장", "병행", "퇴근 후", "시간 부족"]),
    ("사기성 구조로 손해를 봄", ["사기", "속았다", "먹튀", "원금보장"]),
    ("지속하지 못하고 중단함", ["포기", "접었", "그만뒀", "중단"])
]

# -------------------------------
# 3) 유틸 함수
# -------------------------------
def contains_any(text, keywords):
    return any(k in text for k in keywords)

def extract_tags(text, max_tags=3):
    tags = []

    for tag, keywords in TAG_RULES.items():
        if contains_any(text, keywords):
            tags.append(tag)

    # 태그가 하나도 없으면 기본 태그
    if not tags:
        tags.append("운영경험부족")

    return tags[:max_tags]

def extract_causes(text, max_causes=3):
    causes = []

    for cause, keywords in CAUSE_RULES:
        if contains_any(text, keywords):
            causes.append(cause)

    if not causes:
        causes.append("실패 원인이 명확히 드러나지 않음")
        causes.append("운영 과정에서 문제를 겪음")
        causes.append("결과적으로 지속하지 못함")

    # 3개 미만이면 기본 문장 채우기
    while len(causes) < 3:
        fallback_candidates = [
            "운영 과정에서 문제를 겪음",
            "수익화에 어려움을 겪음",
            "결과적으로 지속하지 못함"
        ]
        for fallback in fallback_candidates:
            if fallback not in causes:
                causes.append(fallback)
                break

    return causes[:max_causes]

def make_input_text(question_text):
    return f"부업 실패 사례 분석:\n{question_text.strip()}"

def make_output_text(question_text):
    causes = extract_causes(question_text)
    tags = extract_tags(question_text)

    output = (
        f"실패요인: {causes[0]} / {causes[1]} / {causes[2]}\n"
        f"실패유형: {tags[0]}"
    )

    if len(tags) >= 2:
        output += f", {tags[1]}"
    if len(tags) >= 3:
        output += f", {tags[2]}"

    return output

# -------------------------------
# 4) 입력 읽기
# -------------------------------
rows = []

with open(INPUT_FILE, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f"입력 데이터 수: {len(rows)}개")

# -------------------------------
# 5) T5 학습용 데이터 생성
# -------------------------------
t5_rows = []

for row in rows:
    title = row.get("title", "").strip()
    question_text = row.get("question_text", "").strip()
    link = row.get("link", "").strip()

    if len(question_text) < 30:
        continue

    input_text = make_input_text(question_text)
    output_text = make_output_text(question_text)

    new_row = {
        "input_text": input_text,
        "output_text": output_text,
        "source_title": title,
        "link": link
    }

    t5_rows.append(new_row)

print(f"T5 학습용 데이터 수: {len(t5_rows)}개")

# -------------------------------
# 6) 저장
# -------------------------------
fieldnames = ["input_text", "output_text", "source_title", "link"]

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(t5_rows)

print(f"✅ 저장 완료: {OUTPUT_FILE}")