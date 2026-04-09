import pandas as pd
import re
from difflib import SequenceMatcher

# =========================
# 1. 데이터 불러오기
# =========================
df = pd.read_csv(r"C:\Users\nikki\Desktop\project\naver_cafe_results.csv")

print("원본 데이터:", len(df))

# 결측치 처리
df["title"] = df["title"].fillna("").astype(str)
df["content"] = df["content"].fillna("").astype(str)
df["money_mentions"] = df["money_mentions"].fillna("").astype(str)
df["time_mentions"] = df["time_mentions"].fillna("").astype(str)

# 본문 너무 짧은 글 제거
df = df[df["content"].str.len() >= 100]
print("본문 길이 필터 후:", len(df))


# =========================
# 2. 광고성 글 판별 규칙
# =========================
strong_ad_keywords = [
    "가입비x", "유지비x", "지인영업x", "사재기x",
    "전담멘토", "1:1 케어", "1:1케어", "수익 보장",
    "초보 가능", "초보가능", "함께해요", "클릭",
    "당일 지급", "당일지급"
]

contact_keywords = [
    "카톡 문의", "카톡문의", "오픈채팅", "비밀댓글 남겨주세요",
    "비밀댓글", "설문조사 참여", "설문조사",
    "프로필 링크", "카톡아이디", "상담문의", "링크클릭"
]

domain_patterns = [
    "naver.me",
    "open.kakao.com",
    "fcsmartsystem.com",
    "http://",
    "https://",
    "www."
]

# 아래 단어 2개 이상이면 즉시 삭제
immediate_delete_groups = [
    # 수익 강조
    "고수익", "월 500", "당일지급", "수익인증", "통장내역", "본전회수", "연금성소득",
    # 쉬운 조건
    "초보가능", "누구나가능", "폰하나로", "하루1시간", "재택알바", "타이핑알바",
    # 시스템/조직
    "팀비즈니스", "전담멘토", "1:1케어", "교육시스템", "자동수익", "플랫폼사업",
    # 연락처 유도
    "오픈채팅", "카톡아이디", "비밀댓글", "상담문의", "링크클릭", "설문조사"
]

bad_title_keywords = [
    "모집", "문의", "광고", "홍보", "체험단", "업체", "대행",
    "승인", "이벤트", "지원자", "제작", "받아가세요",
    "공유해요", "성공하세요", "무조건", "찬스", "추천",
    "도와드립니다", "피드 도와", "돈걱정 zero"
]

emoji_pattern = re.compile(
    "[" 
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "]",
    flags=re.UNICODE
)

def count_emojis(text: str) -> int:
    return len(emoji_pattern.findall(text))

def is_bad_title(title: str) -> bool:
    return any(word in title for word in bad_title_keywords)

def has_ad_domain(text: str) -> bool:
    text_lower = text.lower()
    return any(domain in text_lower for domain in domain_patterns)

def has_contact_keyword(text: str) -> bool:
    return any(word in text for word in contact_keywords)

def has_strong_ad_keyword(text: str) -> bool:
    return any(word in text for word in strong_ad_keywords)

def immediate_delete_by_keyword_count(text: str) -> bool:
    count = sum(1 for word in immediate_delete_groups if word in text)
    return count >= 2

def is_ad_content(text: str) -> bool:
    ad_keywords = ['카톡', '문의', '수익', '멘토', '플랫폼', '추천인', '가입비']
    score = sum(1 for word in ad_keywords if word in text)

    has_link = 'http' in text or 'naver.me' in text or 'open.kakao.com' in text
    emoji_count = count_emojis(text)

    if score >= 3:
        return True
    if has_link and score >= 1:
        return True
    if emoji_count > 20:
        return True

    return False

def is_ad_post(title: str, content: str) -> bool:
    text = f"{title}\n{content}"

    if is_bad_title(title):
        return True

    if has_strong_ad_keyword(text):
        return True

    if has_contact_keyword(text):
        return True

    if has_ad_domain(text):
        return True

    if immediate_delete_by_keyword_count(text):
        return True

    if is_ad_content(text):
        return True

    # 이모지 기준은 완화
    if count_emojis(text) >= 10:
        return True

    return False


# =========================
# 3. 실패/피해 경험담 판별
# =========================
experience_keywords = [
    "해봤", "했는데", "해보니", "해보다가", "시작했", "도전했",
    "잃었", "손해", "후회", "환불", "사기", "망했", "망함",
    "안 벌", "수익이 안", "시간만", "그만뒀", "포기",
    "실패", "당했", "날렸", "돈 잃", "피해", "속았",
    "못 받", "자책", "억울", "분노", "화가", "속상"
]

offtopic_keywords = [
    "커피", "이디야", "드립", "다이어트", "건강",
    "청년미래적금", "적금", "MBC", "방송", "썰록"
]

def is_good_failure_story(title: str, content: str) -> bool:
    text = f"{title} {content}"

    has_experience = any(word in text for word in experience_keywords)
    has_offtopic = any(word in text for word in offtopic_keywords)

    if has_offtopic:
        return False

    # 너무 빡세지 않게: 경험 키워드 있으면 통과
    return has_experience


# 광고 제거
df = df[~df.apply(lambda row: is_ad_post(row["title"], row["content"]), axis=1)]
print("광고성 글 제거 후:", len(df))

# 실패 경험담 필터
df = df[df.apply(lambda row: is_good_failure_story(row["title"], row["content"]), axis=1)]
print("실패 경험담 필터 후:", len(df))


# =========================
# 4. 완전 중복 제거
# =========================
df = df.drop_duplicates(subset=["content"])
print("완전 중복 제거 후:", len(df))


# =========================
# 5. 유사 본문 80% 이상 제거
# =========================
def normalize_text(text: str) -> str:
    text = str(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s가-힣]", "", text)
    return text.strip().lower()

normalized_contents = [normalize_text(text) for text in df["content"].tolist()]

keep_indices = []
seen_texts = []

for idx, text in enumerate(normalized_contents):
    is_duplicate = False

    for prev_text in seen_texts:
        similarity = SequenceMatcher(None, text, prev_text).ratio()
        if similarity >= 0.80:
            is_duplicate = True
            break

    if not is_duplicate:
        keep_indices.append(idx)
        seen_texts.append(text)

df = df.iloc[keep_indices].copy()
print("유사 본문 80% 이상 제거 후:", len(df))


# =========================
# 6. 숫자 정보 컬럼 추가
# =========================
df["has_money"] = df["money_mentions"].apply(
    lambda x: 1 if str(x).strip() and str(x).strip().lower() != "nan" else 0
)
df["has_time"] = df["time_mentions"].apply(
    lambda x: 1 if str(x).strip() and str(x).strip().lower() != "nan" else 0
)

print("금액 언급 글 수:", df["has_money"].sum())
print("시간 언급 글 수:", df["has_time"].sum())


# =========================
# 7. 저장
# =========================
output_path = r"C:\Users\nikki\Desktop\project\ai\model\cleaned_data.csv"
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print("\n정제 완료!")
print("최종 데이터 수:", len(df))
print("저장 위치:", output_path)