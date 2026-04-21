from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import csv
import time
import os

print("지식iN 원문 확장(full text) 수집 시작")

INPUT_FILE = "naver_failure_only_v3.csv"
OUTPUT_FILE = "naver_kin_full_raw_v1.csv"

driver = webdriver.Chrome()

# -------------------------------
# 1) CSV 읽기
# -------------------------------
rows = []

with open(INPUT_FILE, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f"입력 후보 수: {len(rows)}개")

# -------------------------------
# 2) 저장 함수
# -------------------------------
FIELDNAMES = [
    "source",
    "keyword",
    "title",
    "description",
    "full_text_old",
    "full_question_text",
    "link",
    "pubDate",
    "text_length_old"
]

def append_row_to_csv(filename, row, fieldnames):
    file_exists = os.path.exists(filename)
    write_header = (not file_exists) or (os.path.getsize(filename) == 0)

    with open(filename, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

# 기존 파일 초기화
open(OUTPUT_FILE, "w", encoding="utf-8-sig").close()

# -------------------------------
# 3) UI 섞인 텍스트 판별
# -------------------------------
def is_ui_noise(text):
    if not text:
        return True

    noise_keywords = [
        "홈 영역",
        "베스트 질문/답변",
        "많이 본 Q&A",
        "지식iN 엑스퍼트",
        "질문",
        "답변",
        "답변 알림 받기",
        "메뉴 더보기",
        "새 창",
        "댓글",
        "나도 궁금해요"
    ]

    hit_count = sum(1 for keyword in noise_keywords if keyword in text)

    # UI 키워드가 너무 많이 섞여 있으면 본문 아님
    if hit_count >= 4:
        return True

    return False

# -------------------------------
# 4) 본문 추출 함수
# -------------------------------
def extract_full_question_text(driver):
    """
    지식iN 페이지 구조가 바뀔 수 있으므로
    본문 후보 selector만 제한적으로 시도한다.
    """
    selector_candidates = [
        "div.se-main-container",          # 네이버 에디터 본문
        "div._endContentsText",           # 구형 본문
        "[class*='question-content']",
        "[class*='QuestionContent']",
        "[class*='c-heading'] + div",
        "[class*='question']"
    ]

    best_text = ""

    for sel in selector_candidates:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)

            for elem in elems:
                text = elem.text.strip()

                if not text:
                    continue

                if len(text) < 50:
                    continue

                if is_ui_noise(text):
                    continue

                # 가장 긴 텍스트를 우선 채택
                if len(text) > len(best_text):
                    best_text = text

        except:
            continue

    return best_text

# -------------------------------
# 5) 텍스트 후처리
# -------------------------------
def clean_full_question_text(text):
    if not text:
        return ""

    remove_lines = [
        "질문",
        "답변",
        "새 창",
        "답변 알림 받기",
        "메뉴 더보기",
        "나도 궁금해요"
    ]

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = []

    for line in lines:
        if line in remove_lines:
            continue

        # 조회수/작성일 같은 메타 제거
        if line.startswith("조회수"):
            continue
        if line.startswith("작성일"):
            continue
        if "조회수" in line and len(line) < 30:
            continue

        cleaned.append(line)

    result = "\n".join(cleaned).strip()
    return result

# -------------------------------
# 6) 링크 순회
# -------------------------------
saved_count = 0

for i, row in enumerate(rows, 1):
    link = row.get("link", "").strip()
    title = row.get("title", "").strip()

    print(f"[{i}/{len(rows)}] 수집 중: {title}")

    if not link:
        continue

    try:
        driver.get(link)
        time.sleep(2.5)

        full_question_text = extract_full_question_text(driver)
        full_question_text = clean_full_question_text(full_question_text)

        # 너무 짧거나 UI성 데이터면 저장 안 함
        if len(full_question_text) < 100:
            print(" -> 본문 너무 짧거나 UI 텍스트라서 건너뜀")
            continue

        if is_ui_noise(full_question_text):
            print(" -> UI 텍스트 비중 높아서 건너뜀")
            continue

        new_row = {
            "source": row.get("source", "").strip(),
            "keyword": row.get("keyword", "").strip(),
            "title": title,
            "description": row.get("description", "").strip(),
            "full_text_old": row.get("full_text", "").strip(),
            "full_question_text": full_question_text,
            "link": link,
            "pubDate": row.get("pubDate", "").strip(),
            "text_length_old": row.get("text_length", "").strip()
        }

        append_row_to_csv(OUTPUT_FILE, new_row, FIELDNAMES)
        saved_count += 1

        print("원문 일부:", full_question_text[:150])

    except WebDriverException as e:
        print("❌ 페이지 접근 실패:", e)
        continue
    except Exception as e:
        print("❌ 기타 에러:", e)
        continue

print(f"\n✅ 원문 확장 저장 완료: {saved_count}개")
print(f"파일명: {OUTPUT_FILE}")

input("엔터 누르면 종료")
driver.quit()