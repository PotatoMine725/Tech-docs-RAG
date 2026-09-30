# 06 · Embeddings và tìm kiếm vector (ChromaDB)
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [01](01-python-for-csharp-devs.md), [05](05-rag-fundamentals.md) · Study time: ~8–10h · Home file của: embedding, chuẩn hoá L2, cosine, ChromaDB/HNSW, batching, cache embedding (SQLite), kế hoạch quota embedding
> Liên quan: throttle/retry chi tiết ở [09](09-llm-api-engineering.md); chunk đưa vào embedding ở [07](07-chunking-and-retrieval.md).

## Vì sao file này quan trọng trong dự án
Retrieval tốt hay dở phần lớn quyết định bởi **embedding** và cách lưu/tìm vector. Đây cũng là chặng **tốn quota** nhất khi xây index (1 request cho mỗi đoạn văn), nên phần lớn code phức tạp (batch, throttle, cache, resume) nằm ở đây. Hiểu file này là hiểu vì sao dự án không "chỉ gọi API rồi lưu".

---

## Level 1 — Basic

### 1.1 Embedding là gì
- **Ý tưởng:** embedding biến một đoạn văn thành một **vector** (danh sách số thực, ở đây 768 số) sao cho các đoạn có **nghĩa gần nhau** thì vector **gần nhau**. Tìm kiếm ngữ nghĩa = tìm các vector gần vector của câu hỏi.
- **C# analogy:** giống `GetHashCode()` nhưng ngược tinh thần: hash tán ngẫu nhiên, còn embedding **giữ** quan hệ nghĩa (mã gần nhau ⇒ nghĩa gần nhau). Vector là `float[768]`.
- **Trong repo này:** hai "mục đích" embedding, gọi là *task type*:
**`src/knowledge_assistant/core/interfaces/embedding.py:5-9`**
```python
class EmbeddingTask(str, Enum):
    """What a text is embedded for. Provider task-type strings live in infrastructure only."""

    DOCUMENT = "document"
    QUERY = "query"
```
  Chuỗi của nhà cung cấp (`RETRIEVAL_DOCUMENT`, `RETRIEVAL_QUERY`) chỉ tồn tại trong infrastructure:
**`src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:28-32`**
```python
TASK_TYPES = {
    EmbeddingTask.DOCUMENT: "RETRIEVAL_DOCUMENT",
    EmbeddingTask.QUERY: "RETRIEVAL_QUERY",
}
FULL_DIM = 3072  # only full-size vectors come back normalized
```
  Đoạn tài liệu được embed với `DOCUMENT`, câu hỏi với `QUERY` (mô hình được huấn luyện để hai loại này khớp nhau).
- **Tại sao:** model là `gemini-embedding-001` — đa ngôn ngữ, nhận nhiều text trong một request, giới hạn đầu vào 2 048 token (lớn hơn chunk 1 600 ký tự) (ADR-0004 D10). [REPO docs/architecture/decisions/0004-gemini-model-selection.md:38-41]
- **Pitfalls:** `[GENERAL]` không trộn embedding từ hai model khác nhau (không gian vector khác nhau, so sánh vô nghĩa). Repo chặn điều này bằng cách đưa **model + số chiều** vào khoá cache và tên collection (1.2).

### 1.2 Số chiều (768) và `model_id`
- **Ý tưởng:** model có thể trả 3 072 chiều; repo yêu cầu **768** (nhỏ hơn 4 lần, tìm nhanh hơn) — quyết định của owner (ADR-0005 D14).
- **Trong repo này:**
**`src/knowledge_assistant/config.py:38-54`**
```python
@dataclass(frozen=True)
class EmbeddingSettings:
    """Embedding settings (ADR-0004 D10, ADR-0005). The model name is pinned here only."""

    model: str
    dim: int
    batch_size: int
    requests_per_minute: int
    tokens_per_minute: int
    max_attempts: int
    timeout_s: float
    cache_path: Path

    @property
    def model_id(self) -> str:
        """Cache / collection key: model name plus output size."""
        return f"{self.model}@{self.dim}"
```
  `model_id` = `"gemini-embedding-001@768"` (đã chạy thử). Nó là **khoá** cho cache và tên collection, nên đổi model hoặc số chiều không bao giờ dùng nhầm dữ liệu cũ.
- **Tại sao:** ADR-0005 D14. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:35-39]
- **Pitfalls:** `[GENERAL]` khi đổi số chiều phải re-embed toàn bộ; cache/collection theo `model_id` đảm bảo điều đó tự nhiên.

### 1.3 Đo "giống nhau": vector chuẩn hoá, tích vô hướng, cosine
- **Ý tưởng:** **Cosine similarity** đo góc giữa hai vector: `1` = cùng hướng, `0` = vuông góc, `-1` = ngược hướng. Nếu cả hai vector đã **chuẩn hoá L2** (độ dài = 1) thì cosine bằng đúng **tích vô hướng** (dot product). Chroma trả **khoảng cách** cosine (`distance = 1 − cosine`), repo đổi lại thành **điểm** `score = 1 − distance` (cao = giống).
- **C# analogy:** `System.Numerics.Vector` `Vector.Dot(a, b)`; chuẩn hoá = `v / v.Length()`.
- **Trong repo này:**
**`src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:37-41`**
```python
def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        raise EmbeddingError("provider returned a zero vector")
    return [v / norm for v in vector]
```
  Điểm và khoảng cách trong store:
**`src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:134-148`**
```python
    def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        size = self.count()
        if size == 0 or top_k <= 0:
            return []
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, size),
            include=["documents", "metadatas", "distances"],
        )
        hits = zip(result["documents"][0], result["metadatas"][0], result["distances"][0])
        ordered = sorted(hits, key=lambda hit: hit[2])
        return [
            RetrievedChunk(chunk=chunk_from_metadata(metadata, document), rank=rank, score=1.0 - float(distance))
            for rank, (document, metadata, distance) in enumerate(ordered, start=1)
        ]
```
  Sắp theo `distance` tăng dần, `rank` đánh từ 1, `score=1.0 - float(distance)`.
- **Số đã kiểm chứng offline:** `l2_normalize([1,2,2])` → `[1/3, 2/3, 2/3]`, tổng bình phương = 1.0. Cosine của `[3,4]` và `[6,8]` = `1.0` (cùng hướng, khác độ dài); `[1,0]` vs `[0,1]` = `0.0`; `[1,0]` vs `[-1,0]` = `-1.0`.
- **Tại sao cosine:** ADR-0005 D17: trên vector đơn vị thì cosine, inner product và L2 xếp hạng **giống nhau**; cosine vẫn đúng ngay cả khi lỡ có vector chưa chuẩn hoá, và dễ đọc điểm nhất. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:69]
- **Pitfalls `[REAL]`:** ở 768 chiều **API không chuẩn hoá** vector (chỉ 3 072 chiều mới có sẵn chuẩn hoá). Phép đo V-1 cho thấy chuẩn L2 ≈ 0.58, nên repo tự chuẩn hoá. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:23]

### 1.4 Vector database (ChromaDB) là gì, và "embedded" nghĩa là gì
- **Ý tưởng:** vector DB lưu (id, vector, tài liệu, metadata) và trả top-k vector gần nhất với một vector truy vấn. Chroma ở đây chạy **nhúng trong tiến trình** (`PersistentClient` ghi thư mục `data/chroma/`), không cần server riêng.
- **C# analogy:** SQLite/LocalDB (nhúng, một thư mục/file) so với SQL Server (client-server). *Collection* ≈ một bảng.
- **Trong repo này:** mỗi arm có **một collection** riêng; tên và metadata mã hoá cấu hình:
**`src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:26-30`**
```python
def collection_name(chunker_config: str, embedding_model_id: str) -> str:
    """`kb_{chunker_config}_{model_id}`; characters Chroma forbids (e.g. '@') become '-'."""
    name = NAME_CHARS.sub("-", f"kb_{chunker_config}_{embedding_model_id}")
    return name.strip("-._") or "kb"

```
  Đã chạy thử: `collection_name("header-1600", "gemini-embedding-001@768")` → `kb_header-1600_gemini-embedding-001-768` (`@` bị đổi thành `-` vì Chroma không cho ký tự đó).
- **Tại sao:** `data/chroma/` nằm trong thư mục repo nhưng **git-ignore**; dựng lại từ file chunk + cache mà **không tốn quota** (ADR-0005 D16). [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:65]
- **Pitfalls:** `[GENERAL]` dữ liệu Chroma là tệp nhị phân của thư viện, không nên commit và không nên sửa tay.

---

## Level 2 — Intermediate

### 2.1 `GeminiEmbedder`: chuẩn hoá và kiểm tra kết quả
- **Ý tưởng:** adapter kiểm **mọi thứ nhận về**: đúng số vector, đúng số chiều; chuẩn hoá khi số chiều < 3 072.
- **Trong repo này:**
**`src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:165-175`**
```python
    def _validate(self, response: Any, expected: int) -> list[list[float]]:
        embeddings = response.embeddings or []
        if len(embeddings) != expected:
            raise EmbeddingError(f"expected {expected} embeddings, got {len(embeddings)}")
        vectors = []
        for embedding in embeddings:
            values = list(embedding.values or [])
            if len(values) != self._settings.dim:
                raise EmbeddingError(f"expected dimension {self._settings.dim}, got {len(values)}")
            vectors.append(l2_normalize(values) if self._settings.dim < FULL_DIM else values)
        return vectors
```
  Đọc: `response.embeddings or []` (None thành list rỗng); lặp từng embedding; `len(values) != dim` → `EmbeddingError`; `l2_normalize(values) if dim < FULL_DIM else values` (biểu thức điều kiện).
- **Tại sao:** dữ liệu sai lặng lẽ (thiếu vector, sai chiều) làm hỏng index mà không ai biết; fail sớm và rõ ràng.
- **Pitfalls:** `[GENERAL]` dựa vào "API luôn trả đúng" là lỗi thường gặp; ở đây coi mọi phản hồi ngoài là không đáng tin.

### 2.2 Batching: `plan_calls` — vì sao mỗi lần gọi có tối đa 45 text **và** nửa ngân sách token
- **Ý tưởng:** gửi nhiều text trong một request tiết kiệm HTTP overhead. Nhưng phép đo **V-1** cho thấy: **mỗi text trong batch tính là 1 request** vào hạn mức (100/phút, 1 000/ngày) — batch **không** tiết kiệm quota, chỉ tiết kiệm độ trễ. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:11-20]
- **Trong repo này:**
**`src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:85-106`**
```python
    def plan_calls(self, texts: list[str]) -> list[list[str]]:
        """At most `batch_size` texts (and the per-minute request limit) and half a minute of tokens per call.

        The throttle admits whole calls, so a call over half the token budget would leave the rest of
        the window unused (ADR-0005 D15): two 45-text Arm B calls (~32K) cannot share a 25K window.
        Greedy, so planning one returned group again gives back that same group: `embed(group)` is one call.
        """
        max_texts = min(self._settings.batch_size, self._settings.requests_per_minute)
        max_tokens = max(1, self._settings.tokens_per_minute // 2)
        batches: list[list[str]] = []
        current: list[str] = []
        current_tokens = 0
        for text in texts:
            tokens = estimate_tokens(text)
            if current and (len(current) >= max_texts or current_tokens + tokens > max_tokens):
                batches.append(current)
                current, current_tokens = [], 0
            current.append(text)
            current_tokens += tokens
        if current:
            batches.append(current)
        return batches
```
  Đọc: `max_texts = min(batch_size=45, requests_per_minute=90)`; `max_tokens = tokens_per_minute // 2 = 12 500`. Duyệt từng text, cắt lô khi đủ `max_texts` **hoặc** thêm text nữa vượt `max_tokens`. Lô cuối flush sau vòng lặp.
- **Đã chạy thử offline** (settings mặc định của config): 100 text mỗi text 1 000 ký tự (≈250 token) → lô `[45, 45, 10]`; 100 text mỗi text 1 400 ký tự (350 token) → `[35, 35, 30]` (chặn bởi trần token: 12 500 // 350 = 35).
- **Tại sao nửa ngân sách:** bộ throttle chỉ nhận **nguyên cuộc gọi**; nếu một cuộc gọi > nửa ngân sách token của cửa sổ 60 giây thì hai cuộc gọi không thể chung một cửa sổ và thông lượng còn một nửa (ADR-0005 D15). [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:41-46]
- **Pitfalls `[REAL]`:** ở RAG-001a verify (F1/F2), **cache** chia theo lát 45 text nhưng **embedder** lại chia nhỏ lần nữa theo trần token: một lỗi sau đó làm mất vector đã trả tiền của các lần gọi trước, và Arm B chạy 39 lần gọi thay vì 25. Sửa: để embedder **sở hữu** quy tắc chia (`plan_calls`) và cache commit theo từng cuộc gọi thực. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:109-118]

### 2.3 Ước lượng token: `chars / 4`
- **Trong repo này:**
**`src/knowledge_assistant/infrastructure/embeddings/throttle.py:10-14`**
```python
CHARS_PER_TOKEN = 4  # ADR-0003 D3; V-1 probe: overestimates real tokens by ~15% (safe side), ADR-0005


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))
```
  `estimate_tokens("a" * 1600)` = 400. Phép đo V-1: ước lượng này **cao hơn ~15%** so với thực tế trên mẫu 3 text (678 vs ≈585) — phía an toàn cho throttling. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:25]
- **Pitfalls:** `[GENERAL]` mẫu chỉ có 3 text, đoạn nhiều code có thể lệch khác; ADR ghi rõ điều này ("code-heavy chunks could differ").

### 2.4 Vòng gọi API của embedder (ý chính; chi tiết retry ở file 09)
**`src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:119-135`**
```python
    def _embed_batch(self, batch: list[str], task: EmbeddingTask) -> list[list[float]]:
        client = self._get_client()
        tokens = sum(estimate_tokens(t) for t in batch)
        config = types.EmbedContentConfig(
            task_type=TASK_TYPES[task], output_dimensionality=self._settings.dim
        )
        attempts = self._settings.max_attempts
        for attempt in range(1, attempts + 1):
            self._throttle.acquire(tokens, requests=len(batch))
            self.http_calls += 1
            self.api_requests += len(batch)
            self.estimated_tokens += tokens
            try:
                response = client.models.embed_content(
                    model=self._settings.model, contents=batch, config=config
                )
                return self._validate(response, len(batch))
```
Đọc: (1) lấy client, ước lượng token, dựng `EmbedContentConfig(task_type, output_dimensionality)`; (2) vòng `for attempt in range(1, attempts+1)`; (3) mỗi lần: `throttle.acquire(tokens, requests=len(batch))` — **trừ `len(batch)` request** (V-1); (4) gọi `client.models.embed_content`; (5) thành công → `_validate` rồi `return`. Phần `except`:
**`src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:136-151`**
```python
            except PROVIDER_ERRORS as error:
                failure = classify_failure(error)
                if failure.status == 429 and not self._logged_first_429:
                    # Logged before the daily-quota check so the classifier can be checked against a real body.
                    self._logged_first_429 = True
                    logger.warning("first HTTP 429 of this run, raw error body: %s", failure.body)
                if failure.daily_quota_id:
                    raise QuotaExhaustedError(
                        f"daily embedding quota exhausted ({failure.daily_quota_id}); "
                        f"resume after the {DAILY_RESET} reset"
                    ) from error
                if not failure.retryable or failure.connection_error:
                    # Connection errors are not retried here (ADR-0005 amendment 2, owner-accepted: indexing is
                    # resumable), but they no longer escape as raw httpx exceptions (RAG-003).
                    raise EmbeddingError(f"embedding request failed: {failure.reason}") from error
                last_error: Exception = error
```
- Nếu 429 **theo ngày** → `QuotaExhaustedError` ngay, không chờ ("resume after the 14:00 UTC+7 reset").
- Nếu không retry được, hoặc lỗi kết nối → `EmbeddingError` (kết nối **không** được retry ở embedder: owner chấp nhận vì việc index có thể chạy tiếp; ADR-0005 Amendment 2). [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:127]
- Còn lại (429 theo phút, 5xx, timeout) → chờ (backoff + jitter, tối đa 120s) rồi thử lại; hết `max_attempts=5` thì `EmbeddingError`.
- **Pitfalls `[REAL]`:** đường "daily-quota 429" chỉ được kiểm bằng **fake**; ADR ghi "no real daily 429 has been seen yet" và nhờ vậy embedder log thân của 429 đầu tiên (đã che key) để đối chiếu khi gặp thật. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:63]

### 2.5 `CachingEmbedder`: chỉ gửi phần chưa có, commit từng cuộc gọi
- **Ý tưởng:** trước khi gọi API, tra SQLite theo khoá `sha256(model_id | task | text)`; chỉ **miss** mới gửi; mỗi cuộc gọi thành công được **commit ngay** vào một transaction trước khi gửi cuộc gọi kế tiếp.
- **Trong repo này:** khoá và mã hoá vector:
**`src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:19-41`**
```python
SCHEMA = """
CREATE TABLE IF NOT EXISTS embeddings (
    key TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    task TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vector BLOB NOT NULL,
    created_at TEXT NOT NULL
)
"""
LOOKUP_CHUNK = 500  # stays under SQLite's bound-parameter limit


def cache_key(model_id: str, task: EmbeddingTask, text: str) -> str:
    return hashlib.sha256(f"{model_id}|{task.value}|{text}".encode("utf-8")).hexdigest()


def _to_blob(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _from_blob(blob: bytes, dim: int) -> list[float]:
    return list(struct.unpack(f"<{dim}f", blob))
```
  Vector lưu dạng **BLOB float32 little-endian** (768 × 4 = 3 072 byte; đã chạy thử: `len(_to_blob([0.1]*768)) == 3072`; đọc lại `0.1` thành `0.10000000149011612` — làm tròn float32).
  Phần `embed`:
**`src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:98-120`**
```python
    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        keys = [cache_key(self.model_id, task, text) for text in texts]
        found = self._lookup(list(dict.fromkeys(keys)))
        self.hits += len(found)

        missing: dict[str, str] = {}  # key -> text, first occurrence order, duplicates sent once
        for key, text in zip(keys, texts):
            if key not in found and key not in missing:
                missing[key] = text
        # The inner embedder owns the split rule (count and token caps); the cache never re-slices,
        # so a group here is exactly one paid call and is committed before the next one is sent.
        pending = list(missing.items())
        start = 0
        for group in self._inner.plan_calls([text for _, text in pending]):
            batch = pending[start : start + len(group)]
            start += len(group)
            if [text for _, text in batch] != list(group):
                raise EmbeddingError("inner plan_calls must return every text once, in order")
            found.update(self._embed_and_store(batch, task))
        if start != len(pending):
            raise EmbeddingError(f"inner plan_calls covered {start} of {len(pending)} texts")

        return [found[key] for key in keys]
```
  Đọc: `dict.fromkeys(keys)` khử trùng khi tra; `missing` giữ thứ tự xuất hiện đầu tiên (text trùng chỉ gửi **một lần**); `self._inner.plan_calls(...)` cho biết nhóm; mỗi nhóm → `_embed_and_store` (commit); cuối cùng trả `[found[key] for key in keys]` — kết quả **đúng thứ tự đầu vào**, kể cả với text trùng.
- **Đã chạy thử offline:** `cache_key(model_id, QUERY, "hello")` và `cache_key(model_id, DOCUMENT, "hello")` cho hai khoá khác nhau (`c7bf0178…` vs `c27715f0…`), đổi `model_id` cũng cho khoá khác (`39e0defc…`) — nên đổi task/model/dim không bao giờ dùng lại vector cũ.
- **Tại sao SQLite (dù CLAUDE.md nói chỉ dùng SQLite khi có nhu cầu cụ thể):** cần (1) ghi **nguyên tử** (một transaction/cuộc gọi trả tiền), (2) **resume** (chạy lại chỉ gửi phần thiếu; dừng lúc 14:00 tiếp tục ngày quota sau). Phương án bị loại: JSONL append (đuôi rách khi crash), `.npy`, dùng Chroma làm cache. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:71-83]
- **Pitfalls:** `[GENERAL]` SQLite connection chỉ dùng trên luồng tạo ra nó — vì vậy GUI mở cache **theo từng lần gọi** (file 03 §3.3).

### 2.6 `ChromaVectorStore`: upsert, tìm, và kiểm tra cấu hình khi mở
- **Trong repo này:** khi mở, nếu collection có sẵn thì so metadata:
**`src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:97-105`**
```python
    def _check_metadata(self, metadata: dict) -> None:
        expected = {
            "hnsw:space": DISTANCE,
            "chunker_config": self.chunker_config,
            "embedding_model_id": self.embedding_model_id,
        }
        wrong = {key: metadata.get(key) for key, value in expected.items() if metadata.get(key) != value}
        if wrong:
            raise VectorStoreError(f"collection {self.name} was built with different settings: {wrong}")
```
  `expected` là dict; `wrong = {key: metadata.get(key) for key, value in expected.items() if metadata.get(key) != value}` là dict comprehension có điều kiện: các khoá khác nhau. Nếu có `wrong`, ném `VectorStoreError` — hai cấu hình sanitize ra cùng tên **vẫn không thể chung một collection** vì metadata giữ giá trị chính xác. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:129]
  Metadata của Chroma **không nhận `None` và không nhận list**, nên `heading_path` (tuple) được lưu thành chuỗi JSON, `source_url=None` bị bỏ qua:
**`src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:32-49`**
```python
def chunk_to_metadata(chunk: DocumentChunk) -> dict[str, str | int]:
    """Every D6 field except `embed_text` (stored as the document). Chroma metadata takes no None and no lists:
    `heading_path` becomes a JSON array string, and a None `source_url` is left out."""
    metadata: dict[str, str | int] = {
        "chunk_id": chunk.chunk_id,
        "source_id": chunk.source_id,
        "document_name": chunk.document_name,
        "heading_path": json.dumps(list(chunk.heading_path), ensure_ascii=False),
        "location_type": chunk.location_type,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
        "display_text": chunk.display_text,
        "content_hash": chunk.content_hash,
        "chunker_config": chunk.chunker_config,
    }
    if chunk.source_url is not None:
        metadata["source_url"] = chunk.source_url
    return metadata
```
  Upsert theo lô 500, kiểm `len(chunks) == len(embeddings)` và mỗi chunk đúng `chunker_config`:
**`src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:115-132`**
```python
    def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        if self._collection is None:
            raise VectorStoreError(f"collection {self.name} was opened read-only and does not exist")
        if len(chunks) != len(embeddings):
            raise ValueError(f"{len(chunks)} chunks but {len(embeddings)} embeddings")
        for chunk in chunks:
            if chunk.chunker_config != self.chunker_config:
                raise VectorStoreError(
                    f"chunk {chunk.chunk_id} is {chunk.chunker_config}, store is {self.chunker_config}"
                )
        for start in range(0, len(chunks), UPSERT_BATCH):
            part = chunks[start : start + UPSERT_BATCH]
            self._collection.upsert(
                ids=[chunk.chunk_id for chunk in part],
                embeddings=embeddings[start : start + UPSERT_BATCH],
                documents=[chunk.embed_text for chunk in part],
                metadatas=[chunk_to_metadata(chunk) for chunk in part],
            )
```
  `embed_text` được lưu làm **document** của Chroma; phần còn lại là metadata. `create=False` mở **chỉ đọc**: collection thiếu được coi là rỗng ([REPO src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:70]).
- **Tại sao:** thay đổi cấu hình không được lặng lẽ tái dùng collection cũ.
- **Pitfalls:** `[GENERAL]` `upsert` = insert-or-update theo `id`; hai lần upsert cùng `chunk_id` không nhân đôi (nền tảng của idempotency ở file 04/05).

---

## Level 3 — Advanced

### 3.1 HNSW và "tìm kiếm gần đúng" (approximate nearest neighbour)
- **Ý tưởng:** tìm chính xác láng giềng gần nhất trong hàng triệu vector là O(N). **HNSW** (Hierarchical Navigable Small World) xây đồ thị nhiều tầng để tìm **gần đúng** nhanh hơn rất nhiều, đổi lại kết quả có thể không tuyệt đối chính xác. Chroma dùng HNSW nội bộ; repo chỉ chọn "không gian khoảng cách" qua metadata `hnsw:space`.
- **C# analogy:** giống index của cơ sở dữ liệu: đổi độ chính xác/không gian lấy tốc độ; ở đây là chỉ mục cho phép tra theo "độ gần".
- **Trong repo này:** [REPO src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:20] (`DISTANCE = "cosine"`), [REPO src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:87] (`"hnsw:space": DISTANCE`). Với chromadb 1.5.9, đặt `hnsw:space` = `configuration.hnsw.space = "cosine"` (đã kiểm trên collection thử). [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:129]
- **Pitfalls `[REAL]`:** một test của `chroma_store` từng fail **một lần** trong một lần chạy full-suite với `InternalError: Error in compaction` (nội bộ Chroma). QC-001 chạy lại **15 lần** (5 riêng, 5 theo module, 5 full-suite) — 0 lần tái hiện; nguyên nhân **chưa xác định**, giả thuyết (chưa xác nhận) là xung đột thời gian khi nhiều `PersistentClient` được tạo/huỷ nhanh trong một tiến trình. Repo để nguyên và **công khai** điều này. [REPO README.md:305-310], [REPO docs/reports/execution/QC-001.md:96-108]
  Bài học: test không xác định (flaky) phải được ghi lại trung thực, không được "chữa" bằng cách xoá test.

### 3.2 Kế hoạch quota: tính toán thật (ADR-0005 D15/D19)
Bảng đo/ước lượng (từ ADR, mô phỏng offline, không gọi API):
| | Arm A | Arm B |
|---|---|---|
| Chunk / text khác nhau | 733 / 709 | 859 / 859 |
| Số lần gọi API | 16 | 25 |
| Text trung bình mỗi lần gọi | 44.3 | 34.4 |
| Token ước lượng | 174 842 | 307 285 |
| Giới hạn ràng buộc | request (90/phút) | token (25K/phút ≈ 70 text/phút) |
| Lần gọi cuối bắt đầu ở | 7.0 phút | 12.0 phút |
[REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:49-57]
- Tổng nhu cầu = 709 + 859 = **1 568 request** > 1 000 request/ngày ⇒ phải chia **hai ngày quota** (reset lúc 14:00 UTC+7): Arm A trước 14:00 hôm đó, Arm B sau 14:00. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:85-99]
- Vì sao Arm A chỉ có 709 text duy nhất trên 733 chunk? Chunk trùng `embed_text` (ví dụ đoạn lặp giữa các phiên bản trong doc #13/#17/#23) chỉ cần embed **một lần**; cache khử trùng. Số đo thật trên đĩa (trong máy này, chỉ đọc): `arm-a.jsonl` 733 dòng / 709 `embed_text` khác nhau; `arm-b.jsonl` 859 / 859.
- **Đọc bảng:** "Binding limit" = ràng buộc nào chặn trước. Arm A: ít token/đoạn (247 trung bình) nên **số request** là nút cổ chai; Arm B: nhiều token/đoạn (358) nên **token** là nút cổ chai.
- **Tại sao quan trọng:** đây là ví dụ về **lập kế hoạch dựa trên số đo** (V-1) thay vì đoán; kế hoạch được owner duyệt trước khi chạy.
- **Pitfalls `[REAL]`:** phép đo V-1 dựa trên ảnh chụp biểu đồ AI Studio của owner (không có giá trị tooltip chính xác) — ADR nêu rõ "evidence limits"; nếu một lỗi quota mâu thuẫn thì phải đo lại. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:27-32]

### 3.3 Tính xác định (determinism) của embedding qua cache
- **Ý tưởng:** lần **miss** đầu tiên trả về vector đã qua float32 (`stored[key] = _from_blob(blob, len(vector))`), giống hệt lần **hit** sau đó, nên kết quả không phụ thuộc cache có sẵn hay không. [REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:159]
- **Tại sao:** đánh giá và thí nghiệm cần tái lập: cùng câu hỏi phải cho cùng vector dù chạy lần đầu hay lần sau. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:83]
- **Pitfalls:** `[GENERAL]` sai số float32 vs float64 có thể đổi thứ tự xếp hạng khi hai điểm gần bằng nhau; repo phá hoà bằng `chunk_id` (file 07).

### 3.4 Hạn chế đã biết (được owner chấp nhận)
- Bộ đếm throttle sống **trong một tiến trình**, restart script là reset. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:128]
- Chưa từng thấy 429 theo ngày thật. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:126]

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Vì sao câu hỏi và đoạn tài liệu dùng hai *task type* khác nhau (`QUERY` vs `DOCUMENT`)?
<details><summary>Đáp án</summary>
Model embedding được huấn luyện để vector "câu hỏi" và vector "tài liệu" khớp nhau khi liên quan; tách task type cho kết quả retrieval tốt hơn. Repo ánh xạ `EmbeddingTask.DOCUMENT` → `RETRIEVAL_DOCUMENT`, `QUERY` → `RETRIEVAL_QUERY` và ghi nhận trong ADR-0004 D10 ([REPO src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:28-31]).
</details>

**B2 (Basic).** `score = 1 − distance`. Nếu Chroma trả `distance = 0.25`, score là bao nhiêu, và hai vector đó gần hay xa?
<details><summary>Đáp án</summary>
`0.75`; khá gần (cosine distance 0 = cùng hướng, 1 = vuông góc). Điểm 0.686 (ngưỡng gate) tương ứng khoảng cách ≈ 0.314.
</details>

**B3 (Basic).** Tính tay: chuẩn hoá vector `[3, 4]`. Độ dài trước và sau?
<details><summary>Đáp án</summary>
Độ dài trước = 5; sau chuẩn hoá `[0.6, 0.8]`, độ dài = 1 (đã chạy thử).
</details>

**I1 (Intermediate).** Với settings mặc định (batch 45, 90 req/phút, 25 000 token/phút), 100 text dài 1 400 ký tự được chia thành các lô nào? Tính bằng tay rồi đối chiếu.
<details><summary>Đáp án</summary>
Mỗi text = ceil(1400/4) = 350 token. Trần token mỗi lô = 25 000 // 2 = 12 500 → 12 500 // 350 = 35 text (trần 45 không chặn trước). Lô: `[35, 35, 30]` (đã chạy `plan_calls` thật với client giả).
</details>

**I2 (Intermediate).** `cache_key(model_id, task, text)` — nếu chỉ đổi `task` từ `DOCUMENT` sang `QUERY` thì khoá thay đổi không? Điều đó ngăn lỗi gì?
<details><summary>Đáp án</summary>
Có (khoá là `sha256("model|task|text")`); ngăn việc dùng lại vector `DOCUMENT` cho một truy vấn `QUERY` (hai vector khác nhau cho cùng một chuỗi). Đã chạy thử: hai khoá khác nhau, và đổi `model_id` cũng khác ([REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:32-33]).
</details>

**I3 (Intermediate).** Đọc `CachingEmbedder.embed`. Đầu vào `["x","y","x"]` (chưa có cache): inner embedder nhận gì và kết quả trả về có độ dài bao nhiêu?
<details><summary>Đáp án</summary>
Inner nhận `["x","y"]` (text trùng chỉ gửi một lần); kết quả có 3 phần tử `[v(x), v(y), v(x)]` theo đúng thứ tự đầu vào (`[found[key] for key in keys]`). Có test tương ứng: `test_duplicate_texts_in_one_call_are_sent_once` ([REPO tests/unit/infrastructure/test_embedding_cache.py:38-43]).
</details>

**A1 (Advanced).** Mô phỏng: cache gửi 5 text theo lô 2 (`plan_calls` → [2,2,1]) và **lần gọi thứ 3 thất bại**. Điều gì nằm trong SQLite và lần chạy lại gửi gì?
<details><summary>Đáp án</summary>
Hai lô đầu (4 vector) đã commit trước khi gửi lô 3; lần chạy lại chỉ gửi text còn thiếu (1 text). Đây chính là kịch bản của `test_misses_are_sent_in_batches_and_each_batch_is_stored` ([REPO tests/unit/infrastructure/test_embedding_cache.py:46-57]) và là lý do cache commit **theo từng cuộc gọi trả tiền** (ADR-0005 D18).
</details>

**A2 (Advanced).** Tính: Arm B có 859 text, ~34.4 text/lần gọi trung bình và bị chặn bởi token (≈70 text/phút). Ước lượng thời gian cuối cùng và so với bảng ADR (12.0 phút).
<details><summary>Đáp án</summary>
859 / 70 ≈ 12.3 phút — cùng bậc với 12.0 phút (ADR); sai khác vì ước lượng thô ("≈70 text/phút", ADR ghi mô phỏng chính xác hơn). Ý chính: thời gian ≈ tổng token / (token mỗi phút); 307 285 / 25 000 ≈ 12.3 phút.
</details>

**A3 (Advanced).** Vì sao `_check_metadata` so sánh cả `hnsw:space` chứ không chỉ tên collection?
<details><summary>Đáp án</summary>
Tên đã được "làm sạch" (`@` → `-`) nên hai cấu hình khác nhau có thể trùng tên; metadata giữ giá trị chính xác nên phát hiện được. Ngoài ra, mở một collection cosine như thể L2 sẽ làm điểm số sai mà không báo lỗi ([REPO src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:97-105], ADR-0005 Amendment 2).
</details>

## Self-check questions
1. Embedding là gì và vì sao "gần nhau" có nghĩa?
2. Cosine, dot product và L2 liên hệ ra sao khi vector đã chuẩn hoá?
3. Vì sao phải tự chuẩn hoá ở 768 chiều?
4. V-1 phát hiện điều gì về batch và quota?
5. Vì sao cache commit theo từng cuộc gọi chứ không theo từng lát 45 text?
6. `model_id` được dùng ở những đâu để ngăn dùng nhầm dữ liệu?
7. HNSW đổi cái gì lấy cái gì?

## Interview Q&A
1. **"Cosine similarity là gì, vì sao dùng thay khoảng cách Euclid?"** — Đo góc, không đo độ dài; trên vector đơn vị xếp hạng như nhau, nhưng cosine vẫn đúng khi vector không chuẩn hoá ([REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:69]).
2. **"Bạn xử lý giới hạn quota của API embedding thế nào?"** — Đo (V-1), throttle cửa sổ trượt tính theo số text, batch ≤45 và nửa ngân sách token, cache SQLite commit từng cuộc gọi, chia hai ngày quota ([REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:41-46,85-99]).
3. **"Vector DB nhúng khác server thế nào?"** — Nhúng: chạy trong tiến trình, dữ liệu là thư mục; không có server để vận hành; đánh đổi là chia sẻ đa tiến trình/luồng hạn chế ([REPO src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:78]).
4. **"Kể một lỗi kiến trúc bạn phát hiện ở tầng embedding."** — Cache và embedder chia batch khác nhau → mất vector đã trả tiền khi lỗi (RAG-001a F1/F2), sửa bằng `plan_calls` ([REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:109-118]).
5. **"Bạn xử lý flaky test thế nào?"** — Chạy lại 15 lần, công khai không tái hiện, không xoá test ([REPO README.md:305-310]).

## Further reading
- Tài liệu chính thức: Google Gemini API — *Embeddings*; Chroma docs — *Collections*, *Distance functions*. `[GENERAL]`
- Malkov & Yashunin, 2016/2018, *Efficient and robust approximate nearest neighbor search using HNSW graphs*. `[GENERAL]`
- Tiếp theo: [07 — Chunking & retrieval](07-chunking-and-retrieval.md).
