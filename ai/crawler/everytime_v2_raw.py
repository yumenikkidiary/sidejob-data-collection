from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, InvalidSessionIdException
import time
import csv
import os


print("에타 원본(raw) 데이터 수집 시작")

driver = webdriver.Chrome()

# -------------------------------
# 1) 로그인
# -------------------------------
driver.get("https://everytime.kr/login")
input("👉 에타 로그인 완료 후 엔터 누르기: ")

# -------------------------------
# 2) 게시판 직접 이동
# -------------------------------
print("👉 원하는 게시판(실패 사례가 나올 가능성이 있는 게시판)으로 직접 이동하고 엔터 눌러")
input("게시판 이동 완료 후 엔터: ")

print("현재 URL:", driver.current_url)
print("게시판 페이지 제목:", driver.title)

time.sleep(2)

# -------------------------------
# 3) 게시판명 가져오기
# -------------------------------
def get_board_name(driver):
    try:
        # 페이지 상단 구조에 따라 달라질 수 있어서 후보 여러 개
        selectors = [
            "h1",
            ".boardname",
            ".title h1",
            "header h1"
        ]
        for sel in selectors:
            try:
                text = driver.find_element(By.CSS_SELECTOR, sel).text.strip()
                if text:
                    return text
            except:
                continue
    except:
        pass
    return ""

board_name = get_board_name(driver)
print("게시판명:", board_name)

# -------------------------------
# 4) 링크 수집
# -------------------------------
def collect_post_links(driver, max_posts=50):
    elems = driver.find_elements(By.CSS_SELECTOR, "article a")

    links = []
    seen = set()

    for el in elems:
        href = el.get_attribute("href")
        if href and "/v/" in href and href not in seen:
            seen.add(href)
            links.append(href)

        if len(links) >= max_posts:
            break

    return links

# -------------------------------
# 5) 상세 페이지에서 원본 추출
# -------------------------------
def crawl_raw_post(driver, url, board_name=""):
    driver.get(url)
    time.sleep(2)

    title = ""
    raw_text = ""
    body = ""

    # 제목
    try:
        title = driver.find_element(By.CSS_SELECTOR, "h2").text.strip()
    except:
        title = ""

    # 상세 페이지 전체 텍스트(raw)
    selectors = [
        ".article",
        "article",
        ".text",
        ".content",
        "body"
    ]

    for sel in selectors:
        try:
            raw_text = driver.find_element(By.CSS_SELECTOR, sel).text.strip()
            if raw_text:
                break
        except:
            continue

    # 본문만 최대한 분리 시도
    body = extract_body_from_raw(raw_text, title)

    return {
        "board_name": board_name,
        "title": title,
        "body": body,
        "raw_text": raw_text,
        "url": url
    }

# -------------------------------
# 6) raw_text에서 본문 추출 (아직 완전 정제 X)
# -------------------------------
def extract_body_from_raw(raw_text, title):
    """
    여기서는 '완벽한 정제'가 아니라
    raw_text에서 본문을 최대한 잘리지 않게 분리하는 게 목표.
    """
    if not raw_text:
        return ""

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    result = []
    title_found = False

    for line in lines:
        if title and line == title:
            title_found = True
            continue

        if not title_found:
            continue

        # 댓글 시작으로 추정되는 부분에서 중단
        if line.startswith("익명") or line.startswith("익명(") or line == "대댓글":
            break

        result.append(line)

    return "\n".join(result).strip()

# -------------------------------
# 7) CSV 저장 함수
# -------------------------------
FIELDNAMES = ["board_name", "title", "body", "raw_text", "url"]

def append_row_to_csv(filename, row, fieldnames):
    file_exists = os.path.exists(filename)
    write_header = (not file_exists) or (os.path.getsize(filename) == 0)

    with open(filename, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

# -------------------------------
# 8) 실행
# -------------------------------
RAW_OUTPUT = "everytime_raw_v2.csv"

# 기존 파일 초기화
open(RAW_OUTPUT, "w", encoding="utf-8-sig").close()

links = collect_post_links(driver, max_posts=50)
print(f"수집된 링크 수: {len(links)}")

saved_count = 0

for i, link in enumerate(links, 1):
    print(f"[{i}/{len(links)}] 수집 중: {link}")

    try:
        row = crawl_raw_post(driver, link, board_name=board_name)
        append_row_to_csv(RAW_OUTPUT, row, FIELDNAMES)
        saved_count += 1

        print("제목:", row["title"])
        print("본문 일부:", row["body"][:100])

    except InvalidSessionIdException:
        print("❌ 브라우저 세션 종료. 지금까지 저장된 데이터는 남아 있음.")
        break
    except WebDriverException as e:
        print("❌ 페이지 수집 실패, 건너뜀:", e)
        continue
    except Exception as e:
        print("❌ 기타 에러, 건너뜀:", e)
        continue

print(f"\n✅ 원본 데이터 저장 완료: {saved_count}개")
print(f"파일명: {RAW_OUTPUT}")

input("엔터 누르면 종료")
driver.quit()