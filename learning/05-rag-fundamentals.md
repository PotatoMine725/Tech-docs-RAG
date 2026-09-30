# 05 · RAG cơ bản: toàn bộ pipeline của repo, từng chặng một
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [01](01-python-for-csharp-devs.md), [03](03-architecture-and-gui.md) · Study time: ~7–9h · Home file của: pipeline end-to-end, corpus & manifest, use case ingest, nhận diện ngôn ngữ, grounding & "insufficient" (hai lớp), `AnswerResult`
> Đi sâu từng chặng ở: [06 embedding & vector search](06-embeddings-and-vector-search.md) · [07 chunking & retrieval](07-chunking-and-retrieval.md) · 08 (prompt/generation) · [09 LLM API](09-llm-api-engineering.md).

## Vì sao file này quan trọng trong dự án
Toàn bộ dự án là **một** pipeline: Documents → Parsing → Chunking → Embedding → ChromaDB → Retrieval → Gemini → Answer + Citation ([REPO CLAUDE.md:5]). Nếu bạn nắm được chuỗi này và biết mỗi chặng nằm ở file nào, mọi file còn lại (evaluation, experiment, GUI) chỉ là "đứng trên" pipeline này. File này là bản đồ; các file 06–09 là chi tiết.

---

## Level 1 — Basic

### 1.1 RAG là gì và giải quyết vấn đề gì
- **Ý tưởng:** LLM (Gemini) không biết tài liệu riêng của bạn và có thể "bịa" (hallucinate). **RAG = Retrieval-Augmented Generation**: (1) *tìm* vài đoạn văn liên quan nhất trong kho tài liệu, (2) đưa các đoạn đó **vào prompt**, (3) bắt LLM trả lời **chỉ dựa trên** các đoạn ấy, kèm trích dẫn. Nếu các đoạn không đủ thông tin thì phải nói thẳng "không đủ".
- **C# analogy:** hãy hình dung một service `Search(question)` trả về top-5 đoạn văn (như Elasticsearch/Lucene), rồi một service thứ hai `Summarize(question, passages)`. LLM chỉ là service thứ hai, có luật "không được dùng kiến thức ngoài".
- **Trong repo này:** luật đó được viết thẳng vào prompt:
**`config/prompts/answer_v2.md:1-4`**
```markdown
You are a documentation assistant for a fixed collection of technical documents.
Answer the QUESTION using ONLY the numbered CONTEXT passages.

Rules:
```
  và vào CLAUDE.md: "answers MUST be grounded in retrieved corpus context; if insufficient, say so explicitly" ([REPO CLAUDE.md:10]).
- **Tại sao:** bài toán của dự án là một trợ lý tài liệu **đáng tin**: tốt hơn là từ chối còn hơn trả lời sai.
- **Pitfalls:** `[GENERAL]` RAG **không** loại bỏ hallucination — nó chỉ giảm rủi ro. Đây là lý do dự án đo lường "correct / hallucination / false_refusal" (file 10).

### 1.2 Hai pha: **offline (xây index)** và **online (trả lời)**
```
OFFLINE (run once, resumable)                        ONLINE (every question)
corpus/*.md ─▶ parse ─▶ normalize ─▶ chunk ─▶ embed ─▶ Chroma     question ─▶ embed(query) ─▶ search ─▶ dedup ─▶ gate
      (24 doc)   (1)       (2)        (3)      (4)      (5)                                                     │
                                                                          answer + citations ◀─ parse ◀─ LLM ◀─ prompt
```
- **Offline:** `normalize_corpus.py` → `build_chunks.py --arm A|B` → `build_index.py --arm A|B` ([REPO README.md:132-136]).
- **Online:** `scripts/ask.py` (CLI) hoặc GUI → cùng một use case `AnswerQuestion.ask` ([REPO src/knowledge_assistant/application/generation/answer_question.py:76-121]).
- **Tại sao tách hai pha:** embedding tài liệu **tốn quota** (1 568 request cho hai arm, xem 06); nên làm một lần, lưu vào Chroma + cache SQLite. Trả lời một câu hỏi chỉ cần embed **1** câu hỏi (thường trúng cache).

### 1.3 Corpus: dữ liệu thật
- **Ý tưởng:** corpus là 24 tài liệu Markdown (chủ yếu Microsoft Learn về C#/.NET/ASP.NET Core) trong `corpus/sources/`; danh sách nằm ở `corpus/manifest.json`. ID chạy 1–29, nhưng **#25 chưa từng tồn tại** (bị bỏ qua lúc chuyển đổi), 4 tài liệu bị loại (14, 19, 24, 27) ở `corpus/excluded/`, nên 28 gốc − 4 loại = 24 chấp nhận. [REPO CLAUDE.md:8]
  Manifest ghi đúng các số này: `counts = {original: 28, accepted: 24, excluded: 4}`, `never_existed_ids = ['25']`, `excluded = [14, 19, 24, 27]` (đọc bằng script offline từ `corpus/manifest.json`).
- **Một điều dễ nhầm:** các tài liệu **là tiếng Anh**, nhưng câu hỏi có thể là tiếng Anh **hoặc tiếng Việt** (ADR-0003 D9). [REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:71-76]
- **Test canh corpus:** bộ ID loại phải đúng bốn số và không có tài liệu loại lẫn trong `sources/`:
**`tests/unit/test_project_structure.py:63-70`**
```python
def test_excluded_corpus_ids_are_exactly_14_19_24_27():
    excluded = {p.name.split("-")[0] for p in (ROOT / "corpus" / "excluded").glob("*.md")}
    assert excluded == EXCLUDED_IDS


def test_excluded_ids_absent_from_sources():
    sources = {p.name.split("-")[0] for p in (ROOT / "corpus" / "sources").glob("*.md")}
    assert not sources & EXCLUDED_IDS
```
- **Tại sao:** luật "MUST NOT dùng tài liệu bị loại; MUST NOT sửa/đánh số lại nguồn". Bình thường hoá (normalize) chỉ diễn ra **trong bộ nhớ** (ADR-0003 D1).
- **Pitfalls:** `[GENERAL]` đừng "dọn" corpus bằng tay — mọi số đo (ground truth, offset) phụ thuộc văn bản gốc; repo còn lưu checksum để phát hiện sửa lén ([REPO docs/snapshots/corpus/source-checksums-premigration.sha256]).

### 1.4 Bảy chặng và file phụ trách
| # | Chặng | Làm gì | Code chính | File ghi chú |
|---|---|---|---|---|
| 1 | Parse | file `.md` → `ParsedDocument` (text Markdown) | `infrastructure/parsing/` | 05 §2.2 |
| 2 | Normalize | bỏ boilerplate, đánh số version-variant, tính section H1–H3 | `markdown_normalizer.py` | ADR-0003 D1 |
| 3 | Chunk | cắt thành đoạn ~1 600 ký tự | `infrastructure/chunking/` | [07](07-chunking-and-retrieval.md) |
| 4 | Embed | đoạn → vector 768 chiều | `gemini_embedder.py` + cache | [06](06-embeddings-and-vector-search.md) |
| 5 | Index | vector + metadata → ChromaDB | `chroma_store.py` | [06](06-embeddings-and-vector-search.md) |
| 6 | Retrieve | embed câu hỏi, tìm top-k, khử trùng | `retrieve.py` | [07](07-chunking-and-retrieval.md) |
| 7 | Generate | prompt → Gemini → JSON → citation | `answer_question.py`, `citations.py` | 08, [09](09-llm-api-engineering.md) |

### 1.5 Hai "lớp từ chối" — khi nào hệ thống nói "không đủ thông tin"
- **Ý tưởng:** có **hai lớp** độc lập:
  1. **Retrieval gate:** nếu điểm giống nhau của đoạn tốt nhất (top-1) **thấp hơn ngưỡng**, hệ thống trả lời từ chối **mà không gọi LLM** (rẻ, nhanh).
  2. **LLM layer:** nếu qua gate, LLM có thể tự trả `"insufficient": true` khi ngữ cảnh không trả lời được.
- **C# analogy:** giống một bộ lọc pre-check (guard clause rẻ tiền) trước khi gọi service đắt tiền, và service đó còn tự có thể từ chối.
- **Trong repo này:**
**`src/knowledge_assistant/application/generation/answer_question.py:1-9`**
```python
"""Ask a question → grounded answer with citations, or an explicit "insufficient information" (RAG-002).

Two insufficient layers (OD-9, retrieval-spec.md):
  (a) retrieval gate: top-1 score < threshold → the LLM is not called, `insufficient_reason="retrieval_gate"`;
  (b) LLM layer: the model answers `"insufficient": true` → `insufficient_reason="llm"`.
An insufficient answer shows the localized message, keeps `missing_information`, and may keep related citations
(owner decision D2, 2026-09-24). Unusable LLM output raises GenerationError, and a provider failure raises an LLMError
(quota | unavailable | other, RAG-003); neither is ever turned into "insufficient".
"""
```
  Đọc ngưỡng:
**`src/knowledge_assistant/config.py:196-211`**
```python
@dataclass(frozen=True)
class RetrievalSettings:
    """top_k = 5 for both arms (ADR-0003 D7). The threshold is the OD-9 retrieval gate, tuned on the dev set, Arm A,
    used for both arms (retrieval-spec.md; RAG-002, 2026-09-26)."""

    top_k: int
    overfetch: int  # extra hits fetched so same-content duplicates can be dropped (RAG-002 addendum 1)
    insufficient_score_threshold: float


def get_retrieval_settings() -> RetrievalSettings:
    return RetrievalSettings(
        top_k=int(os.getenv("TOP_K", "5")),
        overfetch=int(os.getenv("RETRIEVAL_OVERFETCH", "10")),
        insufficient_score_threshold=float(os.getenv("INSUFFICIENT_SCORE_THRESHOLD", "0.686")),
    )
```
  Ngưỡng mặc định `0.686`. Cách suy ra nằm ở file 07 (Level 3).
- **Tại sao:** từ chối bằng gate không tốn request LLM (quota rất hạn chế, xem 09).
- **Pitfalls:** `[GENERAL]` gate với ngưỡng cố định có thể sai (từ chối câu hỏi hợp lệ hoặc cho qua câu hỏi ngoài phạm vi). Repo thừa nhận: ngưỡng chỉ tune trên 6 câu dev của Arm A ([REPO AI_WORKLOG.md:891-892]).

---

## Level 2 — Intermediate

### 2.1 Theo dấu MỘT câu hỏi thật, từ CLI đến câu trả lời
Nguồn số liệu: báo cáo smoke `validation/generation/smoke-2026-09-29.md` (một lần chạy thật trên nhánh `dev`; **không phải dữ liệu đánh giá**, chỉ là quan sát đơn lẻ — đúng như tiêu đề file ghi). Lệnh (Q-DEV-001): `python scripts/ask.py "What is a static class in C#, and can another class inherit from it?" --arm A` (dòng 22 của báo cáo).

| Bước | Ai chạy | Dữ liệu vào → ra | Trong báo cáo smoke |
|---|---|---|---|
| 1. `main` đọc tham số | `scripts/ask.py:213-218` | argv → `args.question`, `args.arm` | — |
| 2. Dựng service | `open_service` → `build_answer_service` | `GeminiLLM`, embedder có cache, store Arm A | — |
| 3. Nhận diện ngôn ngữ | `detect_language(question)` | text → `"en"`/`"vi"` | `language en` |
| 4. Embed câu hỏi (QUERY) | `Retriever.retrieve` → `CachingEmbedder` | text → vector 768 chiều (trúng cache) | `embed_query 1` ms |
| 5. Tìm top-(k+overfetch) | `ChromaVectorStore.search` | vector → 15 hit (5+10) | `retrieve 283` ms |
| 6. Khử trùng theo passage | `dedupe_by_passage` | 15 hit → 5 hit rank 1..5 | `duplicates dropped 0` |
| 7. Gate | `retrieved[0].score < threshold` | 0.7360 ≥ 0.6860 → qua | `top-1 score 0.7360, threshold 0.6860` |
| 8. Dựng prompt | `PromptBuilder.build` | câu hỏi + 5 passage → chuỗi | `prompt answer_v2` |
| 9. Gọi LLM | `GeminiLLM.generate` | prompt → JSON text | `generate 4210` ms, `Model: gemini-3.5-flash-lite (retries 0, fallback no)` |
| 10. Parse + trích dẫn | `parse_answer_json`, `resolve_citations` | JSON → `answer`, `[Citation]` | `Citations: [1] C# classes — C# classes > Static classes` |
| 11. In ra | `render_text` | `AnswerResult` → chuỗi | `Tokens: prompt 1197, output 72` |
Tổng: `total 4494` ms; 1 request LLM, 0 request embedding (báo cáo dòng 14–17: câu hỏi đã có trong cache). [REPO validation/generation/smoke-2026-09-29.md:37-40]

Câu hỏi ngoài corpus (Q-DEV-005, refresh token JWT) đi theo nhánh khác: bước 7 thấy `0.6741 < 0.6860` → **không** gọi LLM; kết quả `Insufficient information: yes (retrieval_gate)`, `Model: none`, `Tokens: none`. [REPO validation/generation/smoke-2026-09-29.md:69-86]

Đây là code điều phối toàn bộ (đọc chậm, đối chiếu bảng trên):
**`src/knowledge_assistant/application/generation/answer_question.py:76-97`**
```python
    def ask(self, question: str) -> AnswerResult:
        start = self._clock()
        language = detect_language(question)
        retrieval = self._retriever.retrieve(question)
        retrieved = retrieval.chunks
        latency = dict(retrieval.latency_ms)
        common = {
            "question": question,
            "language": language,
            "retrieved": retrieved,
            "prompt_version": self._prompts.version,
            "duplicates_dropped": retrieval.duplicates_dropped,
        }

        if retrieved[0].score < self.threshold:
            latency["total"] = (self._clock() - start) * 1000.0
            return AnswerResult(
                answer=self._messages[language], insufficient=True, insufficient_reason=RETRIEVAL_GATE,
                missing_information=None, citations=(), dropped_markers=(), uncited_sentences=0,
                latency_ms=latency, llm=None, **common,
            )

```
**`src/knowledge_assistant/application/generation/answer_question.py:98-121`**
```python
        prompt = self._prompts.build(question, language, retrieved)
        generate_start = self._clock()
        response = self._llm.generate(LLMRequest(prompt=prompt, response_schema=ANSWER_SCHEMA))
        latency["generate"] = (self._clock() - generate_start) * 1000.0  # wall time: model + waits + failed attempts
        latency["retry_wait"] = response.retry_wait_ms  # backoff between attempts (RAG-003)
        latency["throttle_wait"] = response.throttle_wait_ms  # client-side per-minute throttle (RAG-003)
        data = parse_answer_json(response.text)

        answer, citations, dropped = resolve_citations(data["answer"], data["cited_passages"], retrieved)
        missing = data["missing_information"].strip() or None
        insufficient = data["insufficient"]
        latency["total"] = (self._clock() - start) * 1000.0
        return AnswerResult(
            answer=self._messages[language] if insufficient else answer,
            insufficient=insufficient,
            insufficient_reason=LLM_LAYER if insufficient else None,
            missing_information=missing,
            citations=citations,  # when insufficient: related content only (D2)
            dropped_markers=dropped,
            uncited_sentences=0 if insufficient else count_uncited_sentences(answer),
            latency_ms=latency,
            llm=response,
            **common,
        )
```

### 2.2 Dữ liệu biến đổi qua các chặng (kiểu nào ở đâu)
| Sau chặng | Kiểu (định nghĩa ở) | Ý nghĩa |
|---|---|---|
| parse | `ParsedDocument` ([REPO src/knowledge_assistant/core/models/__init__.py:31-45]) | text + `sections` (offset H1–H3) |
| normalize | `ParsedDocument(normalized=True)` | text đã sạch; ghi `normalized.jsonl` |
| chunk | `DocumentChunk` ([REPO src/knowledge_assistant/core/models/__init__.py:48-63]) | `display_text`, `embed_text`, offset, hash |
| embed | `list[list[float]]` | 768 số float mỗi đoạn |
| search | `RetrievedChunk` ([REPO src/knowledge_assistant/core/models/__init__.py:66-73]) | chunk + `rank` + `score` |
| generate | `LLMResponse` ([REPO src/knowledge_assistant/core/interfaces/llm.py:13-33]) | text + token + latency + model dùng |
| answer | `AnswerResult` ([REPO src/knowledge_assistant/core/models/__init__.py:88-106]) | câu trả lời + `citations` + số liệu chẩn đoán |

Bước normalize→chunk **đi qua file** (`normalized.jsonl`, `arm-a.jsonl`, `arm-b.jsonl`), nên chạy lại từng bước được:
**`src/knowledge_assistant/application/ingestion/normalize_corpus.py:35-45`**
```python
class NormalizeCorpus:
    def __init__(self, parser_for: Callable[[str], DocumentParser], normalizer: DocumentNormalizer) -> None:
        self._parser_for = parser_for
        self._normalizer = normalizer

    def run(self, documents: Iterable[Document]) -> list[ParsedDocument]:
        results = []
        for document in documents:
            parsed = self._parser_for(Path(document.path).suffix).parse(document)
            results.append(self._normalizer.normalize(parsed))
        return results
```
**`src/knowledge_assistant/application/ingestion/build_chunks.py:60-77`**
```python
def chunk_to_record(chunk: DocumentChunk) -> dict:
    """One chunk-file line: exactly the D6 fields; the heading path is stored as its citation string."""
    record = {field: getattr(chunk, field) for field in CHUNK_FIELDS}
    record["heading_path"] = HEADING_PATH_SEPARATOR.join(chunk.heading_path)
    return record


def record_to_chunk(record: dict) -> DocumentChunk:
    """Inverse of `chunk_to_record`: one chunk-file line -> a `DocumentChunk` (heading path split back)."""
    values = {field: record[field] for field in CHUNK_FIELDS}
    heading = values["heading_path"]
    values["heading_path"] = tuple(heading.split(HEADING_PATH_SEPARATOR)) if heading else ()
    return DocumentChunk(**values)


def load_chunks(path: Path) -> list[DocumentChunk]:
    """Read a chunk file written by `scripts/ingestion/build_chunks.py` (`arm-a.jsonl`, `arm-b.jsonl`)."""
    return [record_to_chunk(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]
```
  `chunk_to_record` dùng dict comprehension + `getattr` để chép đúng các field trong `CHUNK_FIELDS` (ADR-0003 D6); `heading_path` (tuple) được **nối bằng ` > `** thành chuỗi khi ghi ra file và **tách lại** khi đọc. Vòng khứ hồi này đã chạy thử: `record_to_chunk(chunk_to_record(c)) == c` → `True`.
- **Số thật trên đĩa** (quan sát trong máy này, `data/` là dữ liệu chưa commit trong checkout chính, chỉ đọc): `arm-a.jsonl` có **733** dòng, trong đó **709** `embed_text` khác nhau; `arm-b.jsonl` có **859** dòng, đều khác nhau; khớp ADR-0005 (bảng D19). Dòng đầu Arm A: `chunk_id = 01:header-1600:0000`, `char_start=0`, `char_end=1528`; Arm B: `01:fixed-1600:0000`, `char_end=1600`. Chunk ID tách được bằng `split(":")` → `['01', 'header-1600', '0000']`.
- **Tại sao lưu qua file JSONL:** có thể xem bằng mắt, so sánh hai arm, và index resume được (file 04).

### 2.3 Use case index: "chỉ embed cái chưa có"
- **Ý tưởng:** `IndexCorpus.run` đọc file chunk, hỏi store "id nào đã có", chỉ embed phần còn thiếu, rồi upsert theo lô. Chạy lại là **idempotent** (không nhân đôi, không tốn quota lại).
- **Trong repo này:**
**`src/knowledge_assistant/application/ingestion/index_corpus.py:71-92`**
```python
    def pending(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Chunks whose chunk_id is not in the store yet, in file order."""
        ids = [chunk.chunk_id for chunk in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("chunk file has duplicate chunk_ids")
        present = self._store.get_ids()
        return [chunk for chunk in chunks if chunk.chunk_id not in present]

    def run(self, chunks_path: Path) -> IndexReport:
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        start = self._clock()
        before = dict(self._usage()) if self._usage else {}

        chunks = load_chunks(chunks_path)
        config = chunker_config_of(chunks)
        todo = self.pending(chunks)
        if todo:
            vectors = self._embedder.embed([chunk.embed_text for chunk in todo], EmbeddingTask.DOCUMENT)
            if len(vectors) != len(todo):
                raise ValueError(f"embedder returned {len(vectors)} vectors for {len(todo)} chunks")
            for i in range(0, len(todo), self._upsert_batch):
                self._store.upsert(todo[i : i + self._upsert_batch], vectors[i : i + self._upsert_batch])
```
  `self._store.get_ids()` trả `set[str]` các id đã có; `[chunk for chunk in chunks if chunk.chunk_id not in present]` giữ thứ tự file. `IndexCorpus` chỉ biết `Embedder` và `VectorStore` (interface của core) — Gemini/Chroma được lắp ở script (file 03).
- **Tại sao:** quota embedding miễn phí là 1 000 request/ngày; hai arm cần 1 568 (ADR-0005 D19). Dừng giữa chừng rồi chạy tiếp phải an toàn. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:85-99]
- **Pitfalls:** `[GENERAL]` idempotency dựa trên "id đã có" chỉ đúng nếu id **xác định** (deterministic): chunk id được tạo từ `source_id:chunker_config:index` — cùng đầu vào, cùng id.

### 2.4 Nhận diện ngôn ngữ câu hỏi (vi/en)
- **Ý tưởng:** không dùng thư viện; dùng luật: có ký tự riêng của tiếng Việt (ă â đ ê ô ơ ư) hoặc nguyên âm có dấu thanh → `"vi"`, còn lại `"en"`. Chuỗi được chuẩn hoá **NFC** trước để dấu rời ("a" + ký tự dấu) cũng nhận ra.
- **Trong repo này:**
**`src/knowledge_assistant/application/common/language.py:26-33`**
```python
_VI_PATTERN = re.compile(f"[{_VI_LETTERS}{_VI_LETTERS.upper()}]")


def detect_language(text: str) -> str:
    return VIETNAMESE if _VI_PATTERN.search(unicodedata.normalize("NFC", text)) else ENGLISH


LANGUAGE_NAMES = {ENGLISH: "English", VIETNAMESE: "Vietnamese"}
```
- **Tại sao:** câu trả lời và thông báo "không đủ thông tin" phải theo ngôn ngữ câu hỏi (ADR-0003 D9); trích dẫn (`excerpt`) vẫn giữ tiếng Anh gốc.
- **Đã chạy thử offline:** `"What is dependency injection?"` → `en`; `"Cách sử dụng async void trong C#?"` → `vi`; `"Cach su dung async void"` (Việt không dấu) → `en`; `"café"` → `vi` (é là e có dấu sắc, cũng nằm trong bảng). Hai trường hợp cuối chính là **giới hạn đã biết** ghi trong docstring. [REPO src/knowledge_assistant/application/common/language.py:1-9]
- **Pitfalls:** `[GENERAL]` phát hiện ngôn ngữ bằng luật ký tự là heuristic; người dùng gõ tiếng Việt không dấu sẽ nhận câu trả lời tiếng Anh.

### 2.5 `AnswerResult` — "hợp đồng" đầu ra của use case
Xem class đầy đủ: [REPO src/knowledge_assistant/core/models/__init__.py:88-106]. Điểm cần nhớ:
- `insufficient` + `insufficient_reason`: `"retrieval_gate"` (gate) hoặc `"llm"` (LLM) hoặc `None`.
- Khi `insufficient`, `answer` là **thông báo cục bộ hoá** (từ `config/messages.json`), `citations` chỉ là nội dung **liên quan** (quy tắc D2), không bao giờ là chứng cứ cho câu trả lời.
- `latency_ms` theo chặng: `embed_query`, `retrieve`, `generate` (+ `retry_wait`, `throttle_wait`), `total`.
- `llm` là `None` khi gate từ chối (không gọi LLM).
- **Pitfalls `[REAL]`:** trích dẫn "chỉ liên quan" từng gây tranh luận — ví dụ trường hợp `insufficient` mà vẫn có citation: bộ đánh giá phải phân biệt "từ chối sạch" với "từ chối nhưng trình bày nội dung liên quan như đáp án" (nhãn `hallucination`), xem file 10/11. [REPO src/knowledge_assistant/application/evaluation/metrics/mapping.py:3-12]

---

## Level 3 — Advanced

### 3.1 Vì sao hai "arm": pipeline là một **thí nghiệm có kiểm soát**
- **Ý tưởng:** dự án so sánh hai cách chunking (A: theo heading; B: cửa sổ cố định) trong khi **giữ cố định mọi thứ khác**: model embedding, khoảng cách (cosine), top-k = 5, prompt, model Gemini, bộ câu hỏi. [REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:49-53]
- **Trong repo này:** mỗi arm là một collection Chroma riêng, tên gồm cấu hình chunker + id model:
**`src/knowledge_assistant/composition.py:42-55`**
```python
def open_vector_store(arm: str) -> ChromaVectorStore:
    """The existing collection of one experiment arm; never creates one."""
    chunk_file = get_chunks_dir() / f"arm-{arm.lower()}.jsonl"
    try:
        config = chunker_config_of(load_chunks(chunk_file))
    except FileNotFoundError as error:
        raise VectorStoreError(
            f"chunk file {chunk_file.name} not found; run scripts/ingestion/build_chunks.py, then "
            f"scripts/ingestion/build_index.py --arm {arm}"
        ) from error
    store = ChromaVectorStore(get_chroma_path(), config, get_embedding_settings().model_id, create=False)
    if not store.exists:
        raise VectorStoreError(f"collection {store.name} does not exist; run scripts/ingestion/build_index.py --arm {arm}")
    return store
```
- **Tại sao:** nếu đổi nhiều thứ cùng lúc, kết quả không quy được về nguyên nhân. (Kết quả thí nghiệm ở file 13.)
- **Pitfalls:** `[GENERAL]` "held constant" phải được kiểm chứng; repo có test riêng để Arm B **dùng lại** embedding câu hỏi của Arm A, để hai arm nhìn cùng một vector truy vấn ([REPO tests/unit/test_eval_arm_b_reuses_query_embeddings.py]).

### 3.2 Truy vấn xuyên ngôn ngữ (Việt → Anh)
- **Ý tưởng:** câu hỏi tiếng Việt, tài liệu tiếng Anh. Model embedding đa ngôn ngữ đặt câu hỏi Việt và đoạn Anh cùng ý gần nhau trong không gian vector. ADR-0003 D9: model embedding **phải** đa ngôn ngữ.
- **Bằng chứng trong repo (một ví dụ, không phải bằng chứng chất lượng):** ADR-0004 đo cosine của một truy vấn với đoạn đúng vs đoạn không liên quan: `embedding-001` — câu Việt `0.734` vs `0.516`, câu Anh `0.838` vs `0.513`. [REPO docs/architecture/decisions/0004-gemini-model-selection.md:23-25] ADR ghi rõ "one example, not evidence of quality".
- **Số đo thật trong bảng ngưỡng:** các câu hỏi dev tiếng Việt có top-1 score tương đương tiếng Anh (0.7943, 0.7548 vs 0.7360, 0.7737), nên dùng **một** ngưỡng chung. [REPO docs/specs/retrieval-spec.md:44-53] Cỡ mẫu nhỏ (2 câu/ngôn ngữ), chính spec cũng nói vậy.
- **Pitfalls:** `[GENERAL]` retrieval xuyên ngôn ngữ thường kém hơn cùng ngôn ngữ; đó là lý do đánh giá tách theo ngôn ngữ và có cặp câu song song EN/VI (file 10).

### 3.3 Những thứ RAG này **không** làm (biết giới hạn)
Theo README, các mục thưởng tuỳ chọn `BONUS-001` — hybrid search và query rewriting — **chưa được xây**. [REPO README.md:245] Không có reranker, không có hybrid BM25, không có viết lại câu hỏi. Đây là chủ đề của file 16 (`[GENERAL]`).

### 3.4 Sự cố thật liên quan đến pipeline (đọc để hiểu vì sao code có hình dạng hiện tại)
| Sự cố | Bài học | Nguồn |
|---|---|---|
| `[REAL]` Cùng một đoạn văn lặp nhiều lần trong doc #17/#23/#13, khác nhau chỉ ở URL link → top-k bị chiếm bởi bản sao | over-fetch + khử trùng theo `passage_hash` (file 07) | [REPO docs/specs/retrieval-spec.md:17-21] |
| `[REAL]` Marker `[n]` bị nhận nhầm trong code C# (`args[0]`) | chỉ nhận marker ngoài code (file 08) | [REPO AI_WORKLOG.md:823-825] |
| `[REAL]` Lỗi kết nối/quota của Gemini | wrap thành lỗi core, retry/fallback (file 09) | [REPO docs/architecture/decisions/0004-gemini-model-selection.md:73-81] |

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Liệt kê thứ tự 7 chặng của pipeline và cho biết chặng nào **tốn quota** khi xây index, chặng nào khi trả lời một câu hỏi.
<details><summary>Đáp án</summary>
Parse → Normalize → Chunk → Embed → Index (Chroma) → Retrieve → Generate. Khi xây index: **Embed** (mỗi text = 1 request, ADR-0005 V-1). Khi trả lời: embed câu hỏi (1 request nếu chưa có trong cache) + **1 request LLM** (cộng retry/fallback).
</details>

**B2 (Basic).** Câu hỏi `"Cách sử dụng async void trong C#?"` và `"Cach su dung async void"` nhận ngôn ngữ nào? Vì sao khác nhau?
<details><summary>Đáp án</summary>
`vi` và `en` (đã chạy thử). Luật chỉ tìm ký tự đặc trưng tiếng Việt/nguyên âm có dấu; câu không dấu không có ký tự nào khớp → `en` — giới hạn đã biết ([REPO src/knowledge_assistant/application/common/language.py:1-9]).
</details>

**B3 (Basic).** Điểm top-1 = `0.686` đúng bằng ngưỡng: gate chặn hay cho qua?
<details><summary>Đáp án</summary>
Cho qua. Điều kiện chặn là `retrieved[0].score < self.threshold` (so sánh nghiêm ngặt), và spec ghi rõ "score == threshold passes the gate (strict <)" ([REPO src/knowledge_assistant/application/generation/answer_question.py:90], [REPO docs/specs/retrieval-spec.md:35]).
</details>

**I1 (Intermediate).** Với ba câu dev: Q-DEV-001 top-1 = 0.7360, Q-DEV-002 = 0.7943, Q-DEV-005 = 0.6741; ngưỡng 0.686. Gate làm gì với từng câu và bao nhiêu request LLM được dùng?
<details><summary>Đáp án</summary>
Qua, qua, chặn. 2 request LLM (Q-DEV-001, Q-DEV-002), 0 cho Q-DEV-005 — đúng báo cáo smoke ([REPO validation/generation/smoke-2026-09-29.md:14-16]).
</details>

**I2 (Intermediate).** Ngưỡng 0.686 được suy ra ở đâu (đọc [07 §3.3](07-chunking-and-retrieval.md), home của công thức)? Điều gì xảy ra nếu một câu **trả lời được** trong bộ eval có top-1 = 0.65?
<details><summary>Đáp án</summary>
Công thức và bảng số nằm ở file 07 §3.3 (nguồn: [REPO docs/specs/retrieval-spec.md:38-51]). Ở đây chỉ cần hệ quả: top-1 = 0.65 < 0.686 nên gate từ chối oan (thành `false_refusal`), dù LLM có thể trả lời được — đây chính là rủi ro "ngưỡng tune trên n nhỏ" mà spec cảnh báo.
</details>

**I3 (Intermediate).** Vì sao chunk được ghi ra file JSONL rồi đọc lại, thay vì truyền trực tiếp trong bộ nhớ từ chunker sang indexer?
<details><summary>Đáp án</summary>
Để mỗi bước chạy độc lập, kiểm tra được bằng mắt/so sánh hai arm, và bước index (tốn quota) có thể chạy lại/resume mà không phải chunk lại; `chunk_id` xác định nên idempotent ([REPO src/knowledge_assistant/application/ingestion/build_chunks.py:60-77], [REPO src/knowledge_assistant/application/ingestion/index_corpus.py:71-92]).
</details>

**A1 (Advanced).** Đọc `AnswerQuestion.ask`. Liệt kê **mọi đường thoát** (return hoặc raise) của hàm và điều kiện của từng đường.
<details><summary>Đáp án</summary>
(1) `return AnswerResult(... insufficient_reason=RETRIEVAL_GATE ...)` khi `retrieved[0].score < threshold` (dòng 90–96). (2) `return AnswerResult(...)` cuối hàm (dòng 110–121), với `insufficient` lấy từ JSON của LLM. Đường raise: `retrieve` có thể ném `RetrievalError` (store rỗng / sai số vector); `self._llm.generate` có thể ném `LLMError`; `parse_answer_json` có thể ném `GenerationError`; `retrieved[0]` an toàn vì `Retriever` đã ném khi rỗng. Không đường nào biến lỗi thành "insufficient" ([REPO src/knowledge_assistant/application/generation/answer_question.py:1-9]).
</details>

**A2 (Advanced).** Thiết kế thí nghiệm giấy: nếu muốn thêm một arm C (fixed-size 1 200 ký tự), cần đổi những file/cấu hình nào và **không** được đổi gì để giữ kiểm soát?
<details><summary>Đáp án</summary>
Thêm mục `"C"` vào `config/chunking.json` (`type: fixed_size`, `chunker_config` khác, ví dụ `fixed-1200`) ([REPO config/chunking.json:1-21]); `ARMS` trong `composition.py:28` (`("A","B")`) và các script chọn arm; xây chunk + index cho arm C (tốn quota embedding). **Không** đổi model embedding, cosine, top-k, prompt, model Gemini, bộ câu hỏi (ADR-0003 D7). ADR ghi đây là "optional follow-up experiment: fixed-size 1,200 vs 3,200".
</details>

## Self-check questions
1. Hai pha của RAG là gì; pha nào chạy mỗi câu hỏi?
2. Hai lớp "insufficient" khác nhau thế nào về chi phí?
3. `AnswerResult.llm is None` nghĩa là gì?
4. Vì sao `heading_path` được nối bằng ` > ` khi ghi file?
5. Nêu 3 số về corpus (28/24/4) và ID không tồn tại.
6. Vì sao câu hỏi tiếng Việt vẫn tìm được đoạn tiếng Anh?

## Interview Q&A
1. **"Giải thích RAG bằng ví dụ từ dự án của bạn."** — Câu hỏi được embed, tìm top-5 đoạn trong Chroma, đưa vào prompt cùng luật "chỉ dùng CONTEXT"; LLM trả JSON có `answer`, `cited_passages`, `insufficient` ([REPO config/prompts/answer_v2.md:1-13]).
2. **"Làm thế nào bạn giảm hallucination?"** — Prompt ép dùng context; gate ngăn LLM chạy khi retrieval yếu; citation kiểm được; đánh giá có nhãn `hallucination` và judge kiểm chứng ([REPO src/knowledge_assistant/application/evaluation/metrics/mapping.py:3-12]).
3. **"Tại sao có hai lớp từ chối?"** — Gate rẻ (không tốn LLM) nhưng thô; lớp LLM tinh nhưng tốn request ([REPO src/knowledge_assistant/application/generation/answer_question.py:1-9]).
4. **"Làm sao index resume được?"** — `pending()` chỉ lấy chunk chưa có trong store; cache SQLite giữ vector đã trả tiền ([REPO src/knowledge_assistant/application/ingestion/index_corpus.py:71-77]).
5. **"Giới hạn của pipeline này?"** — Không rerank/hybrid; ngưỡng tune trên n nhỏ; nhận diện ngôn ngữ bằng heuristic ([REPO README.md:245]).

## Further reading
- Lewis et al., 2020, *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (bài báo RAG gốc). `[GENERAL]`
- Tài liệu Chroma và google-genai (docs chính thức của từng thư viện). `[GENERAL]`
- Tiếp theo: [06 — Embeddings & vector search](06-embeddings-and-vector-search.md).
