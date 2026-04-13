from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
import faiss
import pickle
import os


class SimilaritySearchEngine:
    def __init__(self, model_name="jhgan/ko-sroberta-multitask"):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.data = None
        self.texts = None

    def load_data(self, data_path="naver_kin_cleaned.json"):
        """JSON 또는 CSV 데이터 로드"""
        if data_path.endswith(".json"):
            df = pd.read_json(data_path)
        elif data_path.endswith(".csv"):
            df = pd.read_csv(data_path)
        else:
            raise ValueError("지원하지 않는 파일 형식입니다. .json 또는 .csv 파일을 사용하세요.")

        # 컬럼 확인
        required_cols = ["title", "description", "source"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"필수 컬럼이 없습니다: {col}")

        # keyword가 없을 수도 있으니 보정
        if "keyword" not in df.columns:
            df["keyword"] = ""

        # full_text가 없으면 생성
        if "full_text" not in df.columns:
            df["full_text"] = (
                df["title"].fillna("").astype(str).str.strip() + " " +
                df["description"].fillna("").astype(str).str.strip()
            ).str.strip()

        # 너무 짧은 텍스트 제거
        df = df[df["full_text"].fillna("").str.len() >= 20].copy()
        df.reset_index(drop=True, inplace=True)

        self.data = df
        self.texts = df["full_text"].tolist()

        print(f"📊 데이터 로딩 완료: {len(self.data)}개")
        return df

    def build_index(self, data_path="naver_kin_cleaned.json", batch_size=32):
        """정제된 데이터로 FAISS 인덱스 구축"""
        print("📂 데이터 불러오는 중...")
        self.load_data(data_path)

        print(f"📝 {len(self.texts)}개 텍스트 임베딩 생성 중...")
        embeddings = self.model.encode(
            self.texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        # 코사인 유사도용 정규화
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        print("🔍 FAISS 인덱스 구축 중...")
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # 내적 = 정규화 시 cosine similarity 역할
        index.add(embeddings.astype("float32"))

        self.index = index
        print("✅ 인덱스 구축 완료")
        return self

    def search_similar(self, query_text, top_k=5, min_similarity=0.5):
        """유사 사례 검색"""
        if self.index is None or self.data is None:
            raise ValueError("인덱스가 아직 없습니다. 먼저 build_index()를 실행하세요.")

        query_embedding = self.model.encode([query_text], convert_to_numpy=True)
        query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)

        similarities, indices = self.index.search(
            query_embedding.astype("float32"),
            top_k * 3
        )

        results = []
        seen = set()

        for sim, idx in zip(similarities[0], indices[0]):
            if idx == -1:
                continue
            if sim < min_similarity:
                continue

            row = self.data.iloc[idx]
            link = row.get("link", "")

            # 중복 링크 방지
            if link in seen and link != "":
                continue
            if link:
                seen.add(link)

            results.append({
                "similarity_score": float(sim),
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "full_text": row.get("full_text", "")[:300],
                "keyword": row.get("keyword", ""),
                "source": row.get("source", ""),
                "link": row.get("link", "")
            })

            if len(results) >= top_k:
                break

        return results

    def save_index(self, save_dir="models", base_name="similarity_index"):
        """인덱스와 메타데이터 저장"""
        if self.index is None or self.data is None:
            raise ValueError("저장할 인덱스가 없습니다. 먼저 build_index()를 실행하세요.")

        os.makedirs(save_dir, exist_ok=True)

        index_path = os.path.join(save_dir, f"{base_name}.index")
        data_path = os.path.join(save_dir, f"{base_name}_data.pkl")

        faiss.write_index(self.index, index_path)

        with open(data_path, "wb") as f:
            pickle.dump(self.data, f)

        print(f"💾 인덱스 저장 완료:")
        print(f"   - {index_path}")
        print(f"   - {data_path}")

    def load_index(self, save_dir="models", base_name="similarity_index"):
        """저장된 인덱스와 메타데이터 불러오기"""
        index_path = os.path.join(save_dir, f"{base_name}.index")
        data_path = os.path.join(save_dir, f"{base_name}_data.pkl")

        self.index = faiss.read_index(index_path)

        with open(data_path, "rb") as f:
            self.data = pickle.load(f)

        self.texts = self.data["full_text"].tolist()
        print("📦 저장된 인덱스 로딩 완료")
        return self


if __name__ == "__main__":
    engine = SimilaritySearchEngine()

    # 네가 만든 클렌징 파일 경로에 맞춰 수정
    engine.build_index("naver_kin_cleaned.csv")

    test_query = "온라인 쇼핑몰 시작했다가 초기비용만 날리고 접었어요"
    results = engine.search_similar(test_query, top_k=5, min_similarity=0.45)

    print("\n🔍 검색 결과")
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] 유사도: {r['similarity_score']:.3f}")
        print(f"제목: {r['title']}")
        print(f"키워드: {r['keyword']}")
        print(f"출처: {r['source']}")
        print(f"요약: {r['description']}")
        print(f"링크: {r['link']}")

    engine.save_index(save_dir="models", base_name="similarity_index")
    print("\n📦 팀원 전달용 검색 인덱스 저장 완료")