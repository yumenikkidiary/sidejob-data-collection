import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# =========================
# 1. 데이터 불러오기
# =========================
df = pd.read_csv(r"C:\Users\nikki\Desktop\project\ai\model\cleaned_data.csv")

# 추천용 텍스트 만들기
df["title"] = df["title"].fillna("").astype(str)
df["content"] = df["content"].fillna("").astype(str)
df["money_mentions"] = df["money_mentions"].fillna("").astype(str)
df["time_mentions"] = df["time_mentions"].fillna("").astype(str)

df["text"] = (
    df["title"] + " " +
    df["content"] + " " +
    df["content"] + " " +   # 본문 비중 강화
    df["money_mentions"] + " " +
    df["time_mentions"]
)

print("데이터 개수:", len(df))

# =========================
# 2. 모델 로드
# =========================
model = SentenceTransformer("jhgan/ko-sroberta-multitask")

# =========================
# 3. 임베딩 생성
# =========================
embeddings = model.encode(df["text"].tolist(), show_progress_bar=True)

print("벡터화 완료")


# =========================
# 4. 결과 필터
# =========================
def is_valid_result(title, content):
    text = f"{title} {content}"

    # 광고/홍보/유도형 표현
    bad_patterns = [
        "누구나", "가능", "할수있는", "하세요",
        "추천", "무조건", "확실한", "돈걱정",
        "드립니다", "받아가세요", "안하면 후회",
        "놓치면", "기회를", "찬스",
        "고수익", "당일지급", "초보가능",
        "전담멘토", "1:1케어", "1:1 케어",
        "오픈채팅", "카톡", "비밀댓글",
        "상담문의", "링크클릭",
        "절대 손해보지 않는", "함께해요",
        "피드 도와", "도와드립니다",
        "후회없도록", "적극적으로 도와",
        "성공하세요"
    ]

    # 긍정/홍보형 표현
    bad_positive_patterns = [
        "후회안", "후회 안", "성공", "복구",
        "수익", "벌었", "돈 벌", "잘 되고",
        "추천드려요", "좋아요", "괜찮아요",
        "실패리스크 적은", "실패하지 않는"
    ]

    # 부업 관련 키워드
    sidejob_keywords = [
        "부업", "투잡", "재택", "재택부업", "알바",
        "쇼핑몰", "블로그", "애드센스",
        "스마트스토어", "쿠팡", "온라인"
    ]

    # 실패/피해 관련 키워드
    failure_keywords = [
        "실패", "사기", "손해", "후회",
        "환불", "피해", "돈 잃", "망",
        "당했", "속았", "안 벌", "수익이 안",
        "날렸", "못 받", "자책", "억울"
    ]

    # 주제 벗어난 것
    offtopic_keywords = [
        "창업전략", "재테크", "금리인상", "월급쟁이",
        "결혼", "공부방", "아파트", "카나프",
        "적금", "주식"
    ]

    # 부업 관련 키워드가 없으면 제외
    if not any(word in text for word in sidejob_keywords):
        return False

    # 실패/피해 관련 키워드가 없으면 제외
    if not any(word in text for word in failure_keywords):
        return False

    # 광고/홍보성 표현 있으면 제외
    if any(word in text for word in bad_patterns):
        return False

    # 긍정 유도형이면 제외
    if any(word in text for word in bad_positive_patterns):
        return False

    # 오프토픽이면 제외
    if any(word in text for word in offtopic_keywords):
        return False

    return True


# =========================
# 5. 검색어 확장
# =========================
def expand_query(query):
    return [
        query,
        query + " 사기",
        query + " 실패",
        query + " 후회",
        query + " 손해",
        query + " 환불",
        query + " 피해",
        query + " 돈 잃음"
    ]


# =========================
# 6. 추천 함수
# =========================
def recommend(query, top_k=5):
    queries = expand_query(query)

    score_list = []
    for q in queries:
        q_vec = model.encode([q])
        sim = cosine_similarity(q_vec, embeddings).flatten()
        score_list.append(sim)

    # 확장된 검색어 점수 평균
    final_similarity = sum(score_list) / len(score_list)

    # 금액/시간 정보 있는 글에 보너스
    bonus = (
        df["has_money"].fillna(0) * 0.03 +
        df["has_time"].fillna(0) * 0.02
    )

    final_score = final_similarity + bonus
    sorted_indices = final_score.argsort()[::-1]

    print("\n===== 추천 결과 =====\n")

    shown = 0
    for idx in sorted_indices:
        row = df.iloc[idx]

        if not is_valid_result(row["title"], row["content"]):
            continue

        print(f"[유사도: {final_score[idx]:.4f}]")
        print("제목:", row["title"])
        print("금액:", row["money_mentions"])
        print("시간:", row["time_mentions"])
        print("URL:", row["article_url"])
        print("-" * 50)

        shown += 1
        if shown >= top_k:
            break

    if shown == 0:
        print("조건에 맞는 추천 결과가 없어요.")


# =========================
# 7. 반복 실행
# =========================
while True:
    query = input("\n검색어 입력 (종료하려면 엔터): ").strip()

    if query == "":
        break

    recommend(query)