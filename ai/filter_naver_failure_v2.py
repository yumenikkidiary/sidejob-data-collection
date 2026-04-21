import csv

print("실패 사례 필터링 v2 시작")

INPUT_FILE = "naver_kin_cleaned_v2.csv"
FAILURE_OUTPUT = "naver_failure_only_v2.csv"
REVIEW_OUTPUT = "naver_failure_review_v2.csv"

# -------------------------------
# 1) 키워드 사전
# -------------------------------
FAILURE_STRONG = [
    "실패", "망했다", "망함", "사기", "속았다", "접었다", "그만뒀다",
    "손해", "손실", "적자", "돈만 날", "시간만 날", "후회",
    "매출이 안", "수익이 안", "0원", "문을 닫", "철수",
    "포기", "안됨", "안된다", "초기비용만", "사기 당"
]

FAILURE_WEAK = [
    "어려웠", "힘들었", "문제", "부족", "적었", "안 벌", "안 팔",
    "손해봄", "손해만", "적자남", "잘 안됨"
]

SUCCESS_KEYWORDS = [
    "성공", "잘됐다", "잘됨", "벌었다", "수익 났", "매출 나옴",
    "도움 됐", "좋았다", "추천함", "만족", "만족중"
]

QUESTION_KEYWORDS = [
    "추천", "추천 좀", "어떰", "어때", "가능?", "가능함?",
    "해본 사람", "아는 사람", "궁금", "질문", "후기 있나요",
    "어떤가요", "알려주세요", "도와주세요", "뭐가 좋", "있나요",
    "인가요", "일까요", "할까요", "되나요", "가능한가요", "괜찮나요", "맞나요"
]

ALBA_KEYWORDS = [
    "알바 후기", "알바", "시급", "근무", "점장", "매장", "출근", "퇴근"
]

FIRST_PERSON = [
    "저는", "제가", "저도", "제 경우", "제 경험", "직접",
    "내가", "저의", "저한테"
]

STORY_WORDS = [
    "처음", "시작", "시작했", "해봤", "했다가", "했는데",
    "그러다가", "근데", "결국", "그래서", "이후", "하다가",
    "알게 됐", "접었", "그만뒀", "포기했", "망했", "망했다"
]

NUMERIC_WORDS = [
    "만원", "천원", "원", "개월", "달", "주", "일", "%", "년"
]

SIDEJOB_WORDS = [
    "부업", "투잡", "재택", "N잡", "부수입", "추가수입",
    "쿠팡파트너스", "스마트스토어", "쇼핑몰", "이커머스",
    "블로그", "온라인 판매", "매출", "수익", "투자", "초기비용"
]

# -------------------------------
# 2) 점수 함수
# -------------------------------
def count_hits(text, keywords):
    return sum(1 for k in keywords if k in text)

def calc_failure_score(text):
    score = 0
    score += count_hits(text, FAILURE_STRONG) * 4
    score += count_hits(text, FAILURE_WEAK) * 2
    return score

def calc_story_score(text):
    score = 0
    score += count_hits(text, FIRST_PERSON) * 2
    score += count_hits(text, STORY_WORDS) * 3
    score += count_hits(text, NUMERIC_WORDS) * 1
    score += count_hits(text, SIDEJOB_WORDS) * 2
    return score

def calc_noise_score(text):
    score = 0
    score += count_hits(text, SUCCESS_KEYWORDS) * 3
    score += count_hits(text, QUESTION_KEYWORDS) * 3
    score += count_hits(text, ALBA_KEYWORDS) * 4
    return score

# -------------------------------
# 3) 분류 함수
# -------------------------------
def classify_text(title, description, full_text):
    text = f"{title} {description} {full_text}".strip()

    failure_score = calc_failure_score(text)
    story_score = calc_story_score(text)
    noise_score = calc_noise_score(text)

    final_score = failure_score + story_score - noise_score

    # 엄격 실패 사례
    if failure_score >= 4 and story_score >= 4 and final_score >= 6:
        return {
            "label": "failure",
            "failure_score": failure_score,
            "story_score": story_score,
            "noise_score": noise_score,
            "final_score": final_score,
            "reason": "실패 서사 명확"
        }

    # 애매하지만 볼 가치 있음
    if failure_score >= 3 and final_score >= 3:
        return {
            "label": "review",
            "failure_score": failure_score,
            "story_score": story_score,
            "noise_score": noise_score,
            "final_score": final_score,
            "reason": "실패 표현 있으나 애매"
        }

    if story_score >= 5 and final_score >= 2:
        return {
            "label": "review",
            "failure_score": failure_score,
            "story_score": story_score,
            "noise_score": noise_score,
            "final_score": final_score,
            "reason": "경험담형이지만 실패 강도 약함"
        }

    return {
        "label": "drop",
        "failure_score": failure_score,
        "story_score": story_score,
        "noise_score": noise_score,
        "final_score": final_score,
        "reason": "질문/성공/알바/일반글 가능성 높음"
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
    source = row.get("source", "").strip()
    keyword = row.get("keyword", "").strip()
    title = row.get("title", "").strip()
    description = row.get("description", "").strip()
    full_text = row.get("full_text", "").strip()
    link = row.get("link", "").strip()
    pubdate = row.get("pubDate", "").strip()
    text_length = row.get("text_length", "").strip()
    label = row.get("label", "").strip()

    result = classify_text(title, description, full_text)

    new_row = {
        "source": source,
        "keyword": keyword,
        "title": title,
        "description": description,
        "full_text": full_text,
        "link": link,
        "pubDate": pubdate,
        "text_length": text_length,
        "label": label,
        "failure_score": result["failure_score"],
        "story_score": result["story_score"],
        "noise_score": result["noise_score"],
        "final_score": result["final_score"],
        "reason": result["reason"]
    }

    if result["label"] == "failure":
        failure_rows.append(new_row)
    elif result["label"] == "review":
        review_rows.append(new_row)

print(f"실패 사례 유력본: {len(failure_rows)}개")
print(f"검수 필요: {len(review_rows)}개")

# -------------------------------
# 6) 저장
# -------------------------------
fieldnames = [
    "source", "keyword", "title", "description", "full_text",
    "link", "pubDate", "text_length", "label",
    "failure_score", "story_score", "noise_score", "final_score", "reason"
]

with open(FAILURE_OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(failure_rows)

with open(REVIEW_OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(review_rows)

print(f"✅ 저장 완료: {FAILURE_OUTPUT}")
print(f"✅ 저장 완료: {REVIEW_OUTPUT}")