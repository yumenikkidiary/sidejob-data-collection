from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
import time
import csv
import os

print("실패 사례 전용 재수집 시작")

driver = webdriver.Chrome()

# -------------------------------
# 1) 로그인
# -------------------------------
driver.get("https://everytime.kr/login")
input("👉 에타 로그인 완료 후 엔터 누르기: ")

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
    "투잡 망함",
    "쇼핑몰 망함",
    "쿠팡파트너스 안됨",
    "스마트스토어 안됨"
]

target_link_count = 500
max_pages_per_keyword = 12

# -------------------------------
# 3) 제외할 게시판
# -------------------------------
BLOCKED_BOARDS = [
    "홍보게시판",
    "동아리·학회",
    "✏️스터디✏️",
    "중앙동아리 홍보게시판"
]

# -------------------------------
# 4) 광고 필터 강화
# -------------------------------
AD_STRONG_KEYWORDS = [
    "오픈채팅", "open.kakao.com", "카톡", "텔레그램", "문의",
    "상담", "추천인", "제휴", "링크", "클릭", "무료",
    "수익보장", "초보가능", "당일지급", "팀원 모집", "모집",
    "함께해요", "같이 하실", "bit.ly", "tinyurl", "naver.me",
    "www", "http", "체험단", "리딩방", "1:1계정", "전담멘토",
    "공급처", "총판", "구축지원", "납품", "매입"
]

AD_EMOJIS = ["🔥", "⚡", "📢", "💰", "💸", "👆", "👍", "✅"]

def calculate_ad_score(text):
    score = 0

    for k in AD_STRONG_KEYWORDS:
        if k in text:
            score += 3

    emoji_count = sum(text.count(e) for e in AD_EMOJIS)
    score += emoji_count * 2

    return score

def is_ad(text):
    return calculate_ad_score(text) >= 3

# -------------------------------
# 5) 부업 / 실패 / 질문 / 잡담 점수
# -------------------------------
SIDE_JOB_STRONG_KEYWORDS = [
    "부업", "투잡", "재택", "N잡", "부수입", "추가수입",
    "쿠팡파트너스", "스마트스토어", "쇼핑몰", "이커머스",
    "블로그", "온라인 판매", "체험단"
]

SIDE_JOB_WEAK_KEYWORDS = [
    "수익", "매출", "월수입", "초기비용", "투자금", "투자",
    "정산", "광고비", "마케팅", "판매", "주문", "고객", "재고"
]

FAILURE_STRONG_KEYWORDS = [
    "실패", "망했다", "망함", "사기", "속았다", "접었다", "그만뒀다",
    "손해", "손실", "적자", "돈만 날렸다", "시간만 날렸다",
    "매출이 안", "수익이 안", "0원", "문을 닫", "철수", "후회",
    "안됨", "안된다", "포기", "사기 당", "날림"
]

FAILURE_WEAK_KEYWORDS = [
    "어려웠", "힘들었", "문제", "부족", "적었", "안 벌", "안 팔",
    "손해봄", "손해만", "적자남", "잘 안됨"
]

QUESTION_KEYWORDS = [
    "추천", "추천 좀", "어떰", "어때", "가능?", "가능함?",
    "해본 사람", "아는 사람", "궁금", "질문", "후기 있나요",
    "어떤가요", "알려주세요", "도와주세요", "뭐가 좋", "있나요?"
]

CHAT_KEYWORDS = [
    "그냥", "ㅋㅋ", "ㅎㅎ", "ㅠㅠ", "ㅜㅜ", "썰", "잡담", "수다"
]

SUCCESS_HINT_KEYWORDS = [
    "성공", "잘됐다", "잘됨", "벌었다", "수익 났", "매출 나옴",
    "도움 됐", "추천함", "좋았다"
]

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
    score += count_hits(text, QUESTION_KEYWORDS) * 3
    score += count_hits(text, CHAT_KEYWORDS) * 1
    score += count_hits(text, SUCCESS_HINT_KEYWORDS) * 2
    return score

def has_story_structure(text):
    markers = [
        "처음", "시작", "그러다가", "근데", "결국",
        "그래서", "이후", "하다가", "알게 됨", "해봤", "했는데"
    ]
    return any(m in text for m in markers)

def has_numeric_detail(text):
    markers = ["만원", "천원", "원", "개월", "달", "주", "일", "%"]
    return any(m in text for m in markers)

# -------------------------------
# 6) 본문 정리
# -------------------------------
def clean_body(raw, title):
    if not raw:
        return ""

    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    result = []
    started = False

    trash_words = {"쪽지", "신고", "공감", "스크랩", "대댓글"}

    for line in lines:
        if line == title:
            started = True
            continue

        if not started:
            if (
                line == "익명"
                or line == "방금"
                or line.endswith("분 전")
                or line.endswith("시간 전")
                or line.endswith("일 전")
                or line in trash_words
                or line.isdigit()
            ):
                continue
            started = True

        if line.startswith("익명") or line.startswith("익명(") or line == "대댓글":
            break

        if (
            line in trash_words
            or line == "방금"
            or line.endswith("분 전")
            or line.endswith("시간 전")
            or line.endswith("일 전")
            or line.isdigit()
        ):
            continue

        result.append(line)

    return "\n".join(result).strip()

# -------------------------------
# 7) 보드명 추출
# -------------------------------
KNOWN_BOARDS = [
    "광주캠 자유게시판", "여수캠 자유게시판", "비밀게시판", "졸업생게시판",
    "새내기게시판", "시사·이슈", "광주캠 장터게시판", "여수캠 장터게시판",
    "정보게시판", "이벤트게시판", "홍보게시판", "동아리·학회",
    "취업·진로", "전대신문", "✏️스터디✏️", "알바인생..", "중앙동아리 홍보게시판"
]

def extract_board_name(text):
    for board in KNOWN_BOARDS:
        if board in text:
            return board
    return ""

# -------------------------------
# 8) CSV 저장 함수
# -------------------------------
STRICT_FIELDNAMES = [
    "keyword", "board_name", "title", "body", "url",
    "ad_score", "side_score", "failure_score", "noise_score", "final_score", "reason"
]

REVIEW_FIELDNAMES = STRICT_FIELDNAMES

def append_row_to_csv(filename, row, fieldnames):
    file_exists = os.path.exists(filename)
    write_header = (not file_exists) or (os.path.getsize(filename) == 0)

    with open(filename, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

# -------------------------------
# 9) 검색 결과에서 링크 수집
# -------------------------------
collected_links = {}   # url -> {"keyword": ..., "board_name": ...}

for keyword in keywords:
    print(f"\n🔍 키워드 검색 중: {keyword}")

    for page in range(1, max_pages_per_keyword + 1):
        search_url = f"https://everytime.kr/search/all/{keyword}/p/{page}"
        driver.get(search_url)
        time.sleep(2)

        anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
        before_count = len(collected_links)

        for a in anchors:
            href = a.get_attribute("href")
            text = a.text.strip()

            if not href or "/v/" not in href:
                continue

            board_name = extract_board_name(text)

            if board_name in BLOCKED_BOARDS:
                continue

            if href not in collected_links:
                collected_links[href] = {
                    "keyword": keyword,
                    "board_name": board_name
                }

        after_count = len(collected_links)
        print(f"페이지 {page} / 누적 링크 수: {after_count}")

        if after_count == before_count:
            break

        if len(collected_links) >= target_link_count:
            break

    if len(collected_links) >= target_link_count:
        break

print(f"\n✅ 링크 수집 완료: {len(collected_links)}개")

# -------------------------------
# 10) 출력 파일 초기화
# -------------------------------
open("everytime_failure_strict.csv", "w", encoding="utf-8-sig").close()
open("everytime_review_strict.csv", "w", encoding="utf-8-sig").close()

strict_count = 0
review_count = 0

# -------------------------------
# 11) 상세 페이지 크롤링 + 엄격 분류
# -------------------------------
all_links = list(collected_links.keys())

for i, link in enumerate(all_links, 1):
    print(f"[{i}/{len(all_links)}] {link}")

    try:
        driver.get(link)
        time.sleep(2)
    except InvalidSessionIdException:
        print("❌ 브라우저 세션이 끊김. 지금까지 저장된 CSV는 남아 있음.")
        break
    except WebDriverException as e:
        print(f"❌ 페이지 이동 실패, 건너뜀: {e}")
        continue

    try:
        title = driver.find_element(By.CSS_SELECTOR, "h2").text.strip()
    except:
        title = ""

    raw = ""
    selectors = [
        ".article .text",
        "article .text",
        ".text",
        ".content",
        "article"
    ]

    for sel in selectors:
        try:
            raw = driver.find_element(By.CSS_SELECTOR, sel).text.strip()
            if raw:
                break
        except:
            continue

    body = clean_body(raw, title)
    text_all = f"{title}\n{body}".strip()

    body_len = len(body)
    ad_score = calculate_ad_score(text_all)
    side_score = calc_side_job_score(text_all)
    failure_score = calc_failure_score(text_all)
    noise_score = calc_noise_score(text_all)

    if has_story_structure(text_all):
        failure_score += 2
    if has_numeric_detail(text_all):
        failure_score += 1

    final_score = side_score + failure_score - noise_score
    board_name = collected_links[link]["board_name"]
    keyword = collected_links[link]["keyword"]

    # 너무 짧으면 검수 후보도 안 넣음
    if body_len < 50:
        continue

    # 광고는 바로 제외
    if is_ad(text_all):
        continue

    row = {
        "keyword": keyword,
        "board_name": board_name,
        "title": title,
        "body": body,
        "url": link,
        "ad_score": ad_score,
        "side_score": side_score,
        "failure_score": failure_score,
        "noise_score": noise_score,
        "final_score": final_score,
        "reason": ""
    }

    # 엄격한 실패 사례 조건
    if side_score >= 3 and failure_score >= 5 and final_score >= 6:
        row["reason"] = "엄격 조건 통과: 부업성/실패성 높음"
        append_row_to_csv("everytime_failure_strict.csv", row, STRICT_FIELDNAMES)
        strict_count += 1
        continue

    # 검수 필요 조건
    if side_score >= 3 and final_score >= 2:
        row["reason"] = "부업 관련이지만 실패 여부 애매"
        append_row_to_csv("everytime_review_strict.csv", row, REVIEW_FIELDNAMES)
        review_count += 1
        continue

    if failure_score >= 4 and final_score >= 2:
        row["reason"] = "실패 표현은 있으나 부업성 약함"
        append_row_to_csv("everytime_review_strict.csv", row, REVIEW_FIELDNAMES)
        review_count += 1
        continue

print(f"\n✅ 엄격 실패 사례: {strict_count}개")
print(f"✅ 검수 필요: {review_count}개")

input("엔터 누르면 종료")
driver.quit()