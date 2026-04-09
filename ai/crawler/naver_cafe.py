from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import time
import re
import pandas as pd
import urllib.parse
import os


def extract_money(text):
    patterns = [
        r'\d[\d,]*\s*만원',
        r'\d[\d,]*\s*원'
    ]
    results = []
    for pattern in patterns:
        results.extend(re.findall(pattern, text))
    return list(set(results))


def extract_time(text):
    patterns = [
        r'하루\s*\d+\s*시간',
        r'\d+\s*시간',
        r'\d+\s*개월',
        r'\d+\s*주',
        r'\d+\s*일'
    ]
    results = []
    for pattern in patterns:
        results.extend(re.findall(pattern, text))
    return list(set(results))


def make_flags(text):
    keywords = {
        "flag_scam": ["사기"],
        "flag_loss": ["손해", "후회", "망함", "망했다", "실패"],
        "flag_refund": ["환불"],
        "flag_fee": ["강의료", "수업료"],
        "flag_timewaste": ["시간낭비"]
    }

    flags = {}
    for flag_name, words in keywords.items():
        flags[flag_name] = 1 if any(word in text for word in words) else 0
    return flags


def safe_get_text(driver, selectors):
    for by, value in selectors:
        try:
            text = driver.find_element(by, value).text.strip()
            if text:
                return text
        except:
            continue
    return ""


def is_bad_title(title):
    bad_keywords = [
        "모집", "문의", "광고", "홍보", "체험단", "찾습니다",
        "업체", "대행", "승인", "이벤트", "지원자", "제작"
    ]
    return any(word in title for word in bad_keywords)


def is_failure_post(title, content):
    target_keywords = [
        "실패", "후회", "사기", "손해", "환불",
        "강의료", "수업료", "시간낭비", "망함", "망했다"
    ]
    text = f"{title}\n{content}"
    return any(word in text for word in target_keywords)


def save_results(results, filename="naver_cafe_results.csv"):
    df = pd.DataFrame(results)
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"중간 저장 완료: {filename} / 현재 {len(df)}건")


print("1) 코드 시작")
driver = webdriver.Chrome()

driver.get("https://www.naver.com")
input("2) 네이버 로그인 후 엔터를 눌러줘: ")

cafe_id = "20340660"
start_page = 1
end_page = 20   # 일단 20으로 줄여서 안정성 확인
keywords = ["실패", "후회", "손해", "사기", "환불"]

all_links = []

# 1. 링크 수집
for keyword in keywords:
    encoded_keyword = urllib.parse.quote(keyword)
    print(f"\n===== 키워드: {keyword} =====")

    for page in range(start_page, end_page + 1):
        print(f"[{keyword}] {page}페이지 링크 수집 중")

        try:
            search_url = (
                f"https://cafe.naver.com/f-e/cafes/{cafe_id}/menus/0"
                f"?viewType=L&ta=ARTICLE_COMMENT&page={page}&q={encoded_keyword}"
            )

            driver.get(search_url)
            time.sleep(2)

            elements = driver.find_elements(By.CSS_SELECTOR, "a.article")

            page_count = 0
            for el in elements:
                href = el.get_attribute("href")
                text = el.text.strip()

                if href and "/articles/" in href and text:
                    all_links.append((text, href, keyword))
                    page_count += 1

            print(f"   -> {page_count}개 링크 추가")

        except WebDriverException as e:
            print("브라우저 세션 오류 발생:", e)
            print("여기까지 링크 수집 종료")
            break

print(f"\n3) 원본 링크 총합: {len(all_links)}")

# 2. 중복 제거
unique_links = []
seen_ids = set()

for title, href, keyword in all_links:
    try:
        article_id = href.split("/articles/")[-1].split("?")[0]
    except:
        continue

    if article_id not in seen_ids:
        seen_ids.add(article_id)
        unique_links.append((title, href, keyword))

print(f"4) 중복 제거 후 링크 수: {len(unique_links)}")

# 3. 제목 필터
filtered_links = []
for title, href, keyword in unique_links:
    if is_bad_title(title):
        continue
    filtered_links.append((title, href, keyword))

print(f"5) 제목 필터 후 링크 수: {len(filtered_links)}")

# 4. 기존 저장 파일 있으면 이어서 방지용으로 로드 안 하고 새로 시작
results = []
seen_urls = set()

# 혹시 이전 파일이 있으면 이어붙이고 싶을 때 사용 가능
output_file = "naver_cafe_results.csv"
if os.path.exists(output_file):
    try:
        old_df = pd.read_csv(output_file)
        if "article_url" in old_df.columns:
            seen_urls = set(old_df["article_url"].dropna().astype(str).tolist())
            results = old_df.to_dict("records")
            print(f"기존 파일 불러옴: {len(results)}건")
    except:
        print("기존 파일 불러오기 실패, 새로 시작")

# 5. 글 본문 수집
for idx, (list_title, article_url, found_keyword) in enumerate(filtered_links, start=1):
    if article_url in seen_urls:
        continue

    print(f"\n[{idx}/{len(filtered_links)}] 수집 중")
    print("목록 제목:", list_title)

    try:
        driver.get(article_url)
        time.sleep(2)

        driver.switch_to.default_content()
        driver.switch_to.frame("cafe_main")
        time.sleep(1)

        title = safe_get_text(driver, [
            (By.CLASS_NAME, "title_text"),
            (By.CSS_SELECTOR, "h3.title_text")
        ])

        content = safe_get_text(driver, [
            (By.CLASS_NAME, "se-main-container"),
            (By.CSS_SELECTOR, ".ContentRenderer"),
            (By.CSS_SELECTOR, ".article_viewer")
        ])

        if len(content) < 50:
            print("   -> 본문 짧아서 제외")
            continue

        if not is_failure_post(title, content):
            print("   -> 실패/후회성 글 아님, 제외")
            continue

        date = safe_get_text(driver, [
            (By.CLASS_NAME, "date"),
            (By.CSS_SELECTOR, ".article_info .date")
        ])

        views = safe_get_text(driver, [
            (By.CLASS_NAME, "count"),
            (By.CSS_SELECTOR, ".article_info .count")
        ])

        full_text = f"{title}\n{content}"

        money_list = extract_money(full_text)
        time_list = extract_time(full_text)
        flags = make_flags(full_text)

        row = {
            "title": title,
            "content": content,
            "category": "부업",
            "date": date,
            "views": views,
            "money_mentions": ", ".join(money_list),
            "time_mentions": ", ".join(time_list),
            "source": "naver_cafe",
            "cafe_id": cafe_id,
            "search_keyword": found_keyword,
            "article_url": article_url,
            **flags
        }

        results.append(row)
        seen_urls.add(article_url)

        print("   -> 수집 완료")

        # 10건마다 중간 저장
        if len(results) % 10 == 0:
            save_results(results, output_file)

    except WebDriverException as e:
        print("브라우저 세션 오류 발생:", e)
        print("여기까지 저장 후 종료")
        save_results(results, output_file)
        break

    except Exception as e:
        print("   -> 수집 실패:", e)
        continue

# 마지막 저장
save_results(results, output_file)

print("\n6) 최종 저장 완료")
print("파일명: naver_cafe_results.csv")
print("총 수집:", len(results))

input("엔터 누르면 종료: ")
driver.quit()