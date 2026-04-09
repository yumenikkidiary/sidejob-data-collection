import requests
import csv
import html
import re
import time

print("네이버 지식iN 수집 시작")

# -------------------------------
# 1) 네이버 API 키 입력
# -------------------------------
CLIENT_ID = "6RqzkvIKdP1wzcnQQsty"
CLIENT_SECRET = "Ekz7dLvtuk"

# -------------------------------
# 2) 실패 중심 키워드
# -------------------------------
keywords = [
    "부업 실패",
    "투잡 실패",
    "재택부업 실패",
    "스마트스토어 실패",
    "쿠팡파트너스 실패",
    "쇼핑몰 실패",
    "부업 사기",
    "투잡 사기",
    "재택부업 사기",
    "다단계 부업",
    "부업 손해",
    "투잡 손해",
    "부업 적자",
    "스마트스토어 적자",
    "부업 후회",
    "투잡 후회",
    "돈만 날림",
    "시간만 날림",
    "매출이 안 나",
    "수익이 안 나",
    "초기비용 날림",
    "사기 당함",
    "속았다 부업",
    "부업 망함",
    "투잡 망함"
]

DISPLAY = 100
MAX_START = 901
SLEEP_SEC = 0.2

# -------------------------------
# 3) 광고/질문/실패 필터
# -------------------------------
AD_KEYWORDS = [
    "오픈채팅", "카톡", "텔레그램", "문의", "상담", "링크",
    "추천인", "제휴", "클릭", "모집", "팀원 모집",
    "수익보장", "초보가능", "당일지급", "무료",
    "bit.ly", "tinyurl", "naver.me", "open.kakao.com",
    "http", "www", "체험단", "리딩방", "전담멘토", "1:1계정"
]

QUESTION_KEYWORDS = [
    "추천", "추천 좀", "어떰", "어때", "가능?", "가능함?",
    "해본 사람", "아는 사람", "궁금", "질문", "후기 있나요",
    "어떤가요", "알려주세요", "도와주세요", "뭐가 좋"
]

SIDE_JOB_KEYWORDS = [
    "부업", "투잡", "재택", "N잡", "부수입", "추가수입",
    "쿠팡파트너스", "스마트스토어", "쇼핑몰", "이커머스",
    "블로그", "온라인 판매", "제휴", "수익", "매출", "투자", "초기비용"
]

FAILURE_KEYWORDS = [
    "실패", "망했다", "망함", "사기", "속았다", "접었다", "그만뒀다",
    "손해", "손실", "적자", "돈만 날렸다", "시간만 날렸다",
    "매출이 안", "수익이 안", "0원", "문을 닫", "철수", "후회",
    "안됨", "안된다", "포기", "사기 당", "날림"
]

def clean_html_text(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&quot;", '"').replace("&apos;", "'")
    return text.strip()

def calculate_ad_score(text):
    score = 0
    for k in AD_KEYWORDS:
        if k in text:
            score += 3
    return score

def is_ad(text):
    return calculate_ad_score(text) >= 3

def count_hits(text, keywords):
    return sum(1 for k in keywords if k in text)

def calc_side_score(text):
    return count_hits(text, SIDE_JOB_KEYWORDS) * 2

def calc_failure_score(text):
    return count_hits(text, FAILURE_KEYWORDS) * 3

def calc_noise_score(text):
    return count_hits(text, QUESTION_KEYWORDS) * 2

# -------------------------------
# 4) API 호출 함수
# -------------------------------
def search_kin(query, start=1, display=100):
    url = "https://openapi.naver.com/v1/search/kin.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": "sim"
    }

    response = requests.get(url, headers=headers, params=params, timeout=20)
    response.raise_for_status()
    return response.json()

# -------------------------------
# 5) 수집
# -------------------------------
rows = []
seen_links = set()

for keyword in keywords:
    print(f"\n🔍 키워드: {keyword}")

    for start in range(1, MAX_START, DISPLAY):
        try:
            data = search_kin(keyword, start=start, display=DISPLAY)
        except Exception as e:
            print(f"API 호출 실패: {e}")
            break

        items = data.get("items", [])
        if not items:
            break

        added_this_round = 0

        for item in items:
            title = clean_html_text(item.get("title", ""))
            description = clean_html_text(item.get("description", ""))
            link = item.get("link", "")
            pubdate = item.get("pubDate", "")

            if not link or link in seen_links:
                continue

            text_all = f"{title}\n{description}"

            ad_score = calculate_ad_score(text_all)
            side_score = calc_side_score(text_all)
            failure_score = calc_failure_score(text_all)
            noise_score = calc_noise_score(text_all)
            final_score = side_score + failure_score - noise_score

            row = {
                "keyword": keyword,
                "title": title,
                "description": description,
                "link": link,
                "pubDate": pubdate,
                "ad_score": ad_score,
                "side_score": side_score,
                "failure_score": failure_score,
                "noise_score": noise_score,
                "final_score": final_score,
                "is_ad": is_ad(text_all)
            }

            rows.append(row)
            seen_links.add(link)
            added_this_round += 1

        print(f"start={start} / 누적 수집={len(rows)}")

        if added_this_round == 0:
            break

        time.sleep(SLEEP_SEC)

# -------------------------------
# 6) 분리 저장
# -------------------------------
strict_rows = []
review_rows = []

for row in rows:
    if row["is_ad"]:
        continue

    if row["side_score"] >= 2 and row["failure_score"] >= 3 and row["final_score"] >= 4:
        strict_rows.append(row)
    elif row["side_score"] >= 2 and row["final_score"] >= 1:
        review_rows.append(row)
    elif row["failure_score"] >= 3 and row["final_score"] >= 1:
        review_rows.append(row)

fieldnames = [
    "keyword", "title", "description", "link", "pubDate",
    "ad_score", "side_score", "failure_score", "noise_score", "final_score", "is_ad"
]

with open("naver_kin_candidates.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

with open("naver_kin_failure_strict.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(strict_rows)

with open("naver_kin_review.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(review_rows)

print(f"\n✅ 전체 후보: {len(rows)}개")
print(f"✅ 엄격 실패 후보: {len(strict_rows)}개")
print(f"✅ 검수 필요: {len(review_rows)}개")