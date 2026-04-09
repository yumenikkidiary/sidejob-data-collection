import csv

print("지식iN 실패 경험담형 분리 시작")

INPUT_FILE = "naver_kin_failure_strict.csv"
STRICT_OUTPUT_FILE = "naver_kin_story_strict.csv"
REVIEW_OUTPUT_FILE = "naver_kin_story_review.csv"

# -------------------------------
# 1) 질문형 / 잡담형 / 경험담형 키워드
# -------------------------------
QUESTION_STRONG_PATTERNS = [
    "인가요", "일까요", "할까요", "되나요", "가능한가요", "어떤가요",
    "괜찮나요", "맞나요", "추천", "추천 좀", "해본 사람", "아는 사람",
    "궁금", "질문", "알려주세요", "도와주세요", "후기 있나요"
]

QUESTION_WEAK_PATTERNS = [
    "어때", "어떰", "가능?", "괜찮을까요", "뭐가 좋", "뭘 해야",
    "무엇이", "어디서", "왜 그런가요"
]

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

NUMERIC_PATTERNS = [
    "만원", "천원", "원", "개월", "달", "주", "일", "%", "년"
]

SIDE_JOB_PATTERNS = [
    "부업", "투잡", "재택", "N잡", "부수입", "추가수입",
    "쿠팡파트너스", "스마트스토어", "쇼핑몰", "이커머스",
    "블로그", "온라인 판매", "제휴", "매출", "수익", "투자", "초기비용"
]

SUCCESS_PATTERNS = [
    "성공", "잘됐다", "잘됨", "벌었다", "수익 났", "매출 나옴",
    "도움 됐", "좋았다", "추천함"
]

# -------------------------------
# 2) 점수 함수
# -------------------------------
def count_hits(text, keywords):
    return sum(1 for k in keywords if k in text)

def calc_question_score(text):
    score = 0
    score += count_hits(text, QUESTION_STRONG_PATTERNS) * 4
    score += count_hits(text, QUESTION_WEAK_PATTERNS) * 2
    return score

def calc_experience_score(text):
    score = 0
    score += count_hits(text, FIRST_PERSON_PATTERNS) * 3
    score += count_hits(text, STORY_PATTERNS) * 3
    score += count_hits(text, LOSS_PATTERNS) * 4
    score += count_hits(text, NUMERIC_PATTERNS) * 1
    score += count_hits(text, SIDE_JOB_PATTERNS) * 2
    return score

def calc_success_score(text):
    return count_hits(text, SUCCESS_PATTERNS) * 2

def has_enough_length(text):
    return len(text.strip()) >= 40

# -------------------------------
# 3) 분류 함수
# -------------------------------
def classify_story(title, description):
    text = f"{title}\n{description}".strip()

    question_score = calc_question_score(text)
    experience_score = calc_experience_score(text)
    success_score = calc_success_score(text)

    final_score = experience_score - question_score - success_score

    # 아주 짧으면 애매함
    if not has_enough_length(text):
        return {
            "label": "review",
            "question_score": question_score,
            "experience_score": experience_score,
            "success_score": success_score,
            "final_score": final_score,
            "reason": "본문/요약 짧음"
        }

    # 강한 질문형이면 우선 검수로
    if question_score >= 6 and experience_score < 8:
        return {
            "label": "review",
            "question_score": question_score,
            "experience_score": experience_score,
            "success_score": success_score,
            "final_score": final_score,
            "reason": "질문형 비중 높음"
        }

    # 경험담형 엄격 통과
    if experience_score >= 10 and final_score >= 5:
        return {
            "label": "strict",
            "question_score": question_score,
            "experience_score": experience_score,
            "success_score": success_score,
            "final_score": final_score,
            "reason": "실패 경험담형 가능성 높음"
        }

    # 중간 지대는 검수
    if experience_score >= 6 and final_score >= 1:
        return {
            "label": "review",
            "question_score": question_score,
            "experience_score": experience_score,
            "success_score": success_score,
            "final_score": final_score,
            "reason": "경험담 가능성 있으나 애매"
        }

    return {
        "label": "drop",
        "question_score": question_score,
        "experience_score": experience_score,
        "success_score": success_score,
        "final_score": final_score,
        "reason": "질문형/일반 정보형 가능성 높음"
    }

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
# 5) 분류
# -------------------------------
strict_rows = []
review_rows = []

for row in rows:
    keyword = row.get("keyword", "").strip()
    title = row.get("title", "").strip()
    description = row.get("description", "").strip()
    link = row.get("link", "").strip()
    pubdate = row.get("pubDate", "").strip()

    result = classify_story(title, description)

    new_row = {
        "keyword": keyword,
        "title": title,
        "description": description,
        "link": link,
        "pubDate": pubdate,
        "question_score": result["question_score"],
        "experience_score": result["experience_score"],
        "success_score": result["success_score"],
        "final_score": result["final_score"],
        "reason": result["reason"]
    }

    if result["label"] == "strict":
        strict_rows.append(new_row)
    elif result["label"] == "review":
        review_rows.append(new_row)

print(f"경험담형 엄격 후보: {len(strict_rows)}개")
print(f"검수 필요: {len(review_rows)}개")

# -------------------------------
# 6) 저장
# -------------------------------
fieldnames = [
    "keyword", "title", "description", "link", "pubDate",
    "question_score", "experience_score", "success_score", "final_score", "reason"
]

with open(STRICT_OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(strict_rows)

with open(REVIEW_OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(review_rows)

print(f"✅ 저장 완료: {STRICT_OUTPUT_FILE}")
print(f"✅ 저장 완료: {REVIEW_OUTPUT_FILE}")