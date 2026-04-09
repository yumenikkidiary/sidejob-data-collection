import csv

print("부업 실패 사례 분리 시작")

INPUT_FILE = "everytime_high_quality.csv"
FAILURE_OUTPUT_FILE = "everytime_failure_candidates.csv"
REVIEW_OUTPUT_FILE = "everytime_review_needed.csv"

# -------------------------------
# 1) 키워드 사전
# -------------------------------
SIDE_JOB_STRONG_KEYWORDS = [
    "부업", "투잡", "재택", "N잡", "부수입", "추가수입",
    "쿠팡파트너스", "스마트스토어", "쇼핑몰", "이커머스",
    "블로그", "체험단", "온라인 판매", "제휴", "공모전", "디자인 수익"
]

SIDE_JOB_WEAK_KEYWORDS = [
    "수익", "매출", "월수입", "초기비용", "투자금", "투자",
    "정산", "광고비", "마케팅", "판매", "주문", "고객", "재고"
]

FAILURE_STRONG_KEYWORDS = [
    "실패", "망했다", "망함", "사기", "속았다", "접었다", "그만뒀다",
    "손해", "손실", "적자", "돈만 날렸다", "시간만 날렸다",
    "매출이 안", "수익이 안", "0원", "문을 닫", "철수", "후회"
]

FAILURE_WEAK_KEYWORDS = [
    "안됐다", "안됨", "안된다", "포기", "어려웠", "힘들었", "문제",
    "부족", "적었", "안 벌", "안 팔", "손해봄", "손해만", "적자남"
]

QUESTION_CHAT_KEYWORDS = [
    "추천 좀", "추천해주세요", "어떰", "어때", "해본 사람", "아는 사람",
    "가능?", "가능함?", "뭐가 좋", "질문", "궁금", "어떤가요",
    "후기 있나요", "도와주세요", "알려주세요"
]

CHAT_ONLY_KEYWORDS = [
    "잡담", "그냥", "ㅋㅋ", "ㅎㅎ", "ㅜ", "ㅠ", "썰", "수다"
]

SUCCESS_HINT_KEYWORDS = [
    "성공", "잘됐다", "잘됨", "벌었다", "수익 났", "매출 나옴",
    "도움 됐", "추천함", "좋았다"
]

# -------------------------------
# 2) 점수 함수
# -------------------------------
def count_hits(text, keywords):
    return sum(1 for k in keywords if k in text)

def calc_side_job_score(text):
    score = 0
    score += count_hits(text, SIDE_JOB_STRONG_KEYWORDS) * 3
    score += count_hits(text, SIDE_JOB_WEAK_KEYWORDS) * 1
    return score

def calc_failure_score(text):
    score = 0
    score += count_hits(text, FAILURE_STRONG_KEYWORDS) * 4
    score += count_hits(text, FAILURE_WEAK_KEYWORDS) * 2
    return score

def calc_noise_score(text):
    score = 0
    score += count_hits(text, QUESTION_CHAT_KEYWORDS) * 3
    score += count_hits(text, CHAT_ONLY_KEYWORDS) * 1
    score += count_hits(text, SUCCESS_HINT_KEYWORDS) * 2
    return score

def has_story_structure(text):
    story_markers = [
        "처음", "시작", "그러다가", "근데", "결국",
        "그래서", "이후", "하다가", "알게 됨", "해봤", "했는데"
    ]
    return any(marker in text for marker in story_markers)

def has_numeric_detail(text):
    numeric_markers = ["만원", "천원", "원", "개월", "달", "주", "일", "%", "3개월", "6개월"]
    return any(marker in text for marker in numeric_markers)

# -------------------------------
# 3) 분류 함수
# -------------------------------
def classify_row(title, body):
    text = f"{title}\n{body}".strip()

    side_score = calc_side_job_score(text)
    failure_score = calc_failure_score(text)
    noise_score = calc_noise_score(text)

    if has_story_structure(text):
        failure_score += 2

    if has_numeric_detail(text):
        failure_score += 1

    body_len = len(body.strip())

    # 너무 짧으면 실패 사례로 보기 어려움
    if body_len < 50:
        return {
            "label": "review",
            "side_score": side_score,
            "failure_score": failure_score,
            "noise_score": noise_score,
            "final_score": failure_score + side_score - noise_score,
            "reason": "본문 짧음"
        }

    final_score = failure_score + side_score - noise_score

    # 강한 실패 사례
    if side_score >= 3 and failure_score >= 4 and final_score >= 6:
        return {
            "label": "failure",
            "side_score": side_score,
            "failure_score": failure_score,
            "noise_score": noise_score,
            "final_score": final_score,
            "reason": "부업+실패 표현 충분"
        }

    # 부업 관련은 맞지만 실패 사례가 애매한 경우
    if side_score >= 3 and final_score >= 3:
        return {
            "label": "review",
            "side_score": side_score,
            "failure_score": failure_score,
            "noise_score": noise_score,
            "final_score": final_score,
            "reason": "부업 관련이나 실패 여부 애매"
        }

    # 실패 같긴 한데 부업성이 약한 경우
    if failure_score >= 4 and final_score >= 3:
        return {
            "label": "review",
            "side_score": side_score,
            "failure_score": failure_score,
            "noise_score": noise_score,
            "final_score": final_score,
            "reason": "실패 표현 있으나 부업성 약함"
        }

    return {
        "label": "drop",
        "side_score": side_score,
        "failure_score": failure_score,
        "noise_score": noise_score,
        "final_score": final_score,
        "reason": "잡담/질문/관련성 낮음"
    }

# -------------------------------
# 4) CSV 읽기
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
failure_rows = []
review_rows = []

for row in rows:
    title = row.get("title", "").strip()
    body = row.get("body", "").strip()
    url = row.get("url", "").strip()

    result = classify_row(title, body)

    new_row = {
        "title": title,
        "body": body,
        "url": url,
        "side_score": result["side_score"],
        "failure_score": result["failure_score"],
        "noise_score": result["noise_score"],
        "final_score": result["final_score"],
        "reason": result["reason"]
    }

    if result["label"] == "failure":
        failure_rows.append(new_row)
    elif result["label"] == "review":
        review_rows.append(new_row)

print(f"실패 사례 후보: {len(failure_rows)}개")
print(f"검수 필요: {len(review_rows)}개")

# -------------------------------
# 6) 저장
# -------------------------------
fieldnames = [
    "title", "body", "url",
    "side_score", "failure_score", "noise_score", "final_score", "reason"
]

with open(FAILURE_OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(failure_rows)

with open(REVIEW_OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(review_rows)

print(f"✅ 저장 완료: {FAILURE_OUTPUT_FILE}")
print(f"✅ 저장 완료: {REVIEW_OUTPUT_FILE}")