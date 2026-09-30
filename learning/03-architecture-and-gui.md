# 03 · Kiến trúc phân lớp, ports & adapters, composition root, và GUI (PySide6 MVVM + thread)
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [01](01-python-for-csharp-devs.md), [01b](01b-python-code-reading-guide.md) · Study time: ~8–10h · Home file của: layers, dependency rule, ports & adapters, composition root, architecture test, ADR, MVVM, Qt thread pool

## Vì sao file này quan trọng trong dự án
Dự án này cố ý được chia lớp để (1) đổi Gemini/Chroma/định dạng file mà không đụng logic, (2) test **offline** (không key, không mạng), (3) cho phép nhiều "điểm vào" (script CLI, GUI, eval runner) dùng chung một use case. Nếu bạn hiểu file này, bạn sẽ biết **code nào được phép import code nào**, và vì sao có một test tự động canh chừng điều đó.

---

## Level 1 — Basic

### 1.1 Bốn lớp và luật phụ thuộc (dependency rule)
- **Ý tưởng:** code được chia thành 4 lớp; mũi tên = "được phép import":
  ```
  presentation ──▶ application ──▶ core ◀── infrastructure
     (GUI PySide6)   (use case)    (model, interface, exception)   (Gemini, Chroma, parser, chunker, SQLite)
  ```
  `core` ở giữa và **không import ai**. `infrastructure` *cài đặt* các interface của `core`. `application` chỉ biết interface của `core`, không biết Gemini/Chroma. `presentation` (GUI) không chứa business logic.
- **C# analogy:** Clean/Onion Architecture với các project: `Domain` (core), `Application`, `Infrastructure`, `UI`. "Project reference" chỉ trỏ vào trong. Ở đây không có project riêng: chỉ là **thư mục** `src/knowledge_assistant/{core,application,infrastructure,presentation}`, luật được giữ bằng **test** (xem 2.4), không phải bằng compiler.
- **Trong repo này:**
**`docs/architecture/system-architecture.md:3-8`**
```markdown
Layers: presentation -> application -> core <- infrastructure.
- core: domain models, interfaces, exceptions; no PySide6, ChromaDB, Gemini or format-specific dependency.
- application: use cases (ingestion, retrieval, generation, citation, evaluation); depends on core interfaces only.
- infrastructure: parsers, chunkers, embeddings, ChromaDB, Gemini, persistence; implements core interfaces.
- presentation: PySide6 desktop GUI; no business logic.
Enforced by tests/unit/test_project_structure.py (core/application import checks).
```
  Luật gốc ở CLAUDE.md rule 3: "Core MUST NOT import PySide6/ChromaDB/Gemini/format-specific code; application MUST depend on core interfaces only; GUI MUST NOT hold business logic." [REPO CLAUDE.md:7]
- **Tại sao làm vậy:** thay Gemini bằng nhà cung cấp khác, hoặc Chroma bằng kho vector khác, chỉ cần viết adapter mới. Ngoài ra `core` + `application` chạy được không cần cài `chromadb`/`google-genai`, nên test nhanh và không tốn quota.
- **Pitfalls:** `[GENERAL]` phân lớp quá đà (nhiều lớp mà logic mỏng) làm code dài; repo giữ gọn: `core` chỉ có models/interfaces/exceptions ([REPO src/knowledge_assistant/core/models/__init__.py:1-126]).

### 1.2 Bản đồ thư mục (đọc code theo lớp)
| Lớp | Thư mục | Có gì (ví dụ thật) |
|---|---|---|
| core | `src/knowledge_assistant/core/` | `models/` (Document, DocumentChunk, Citation, AnswerResult), `interfaces/` (LLM, Embedder, VectorStore, Chunker, Parser, RecordStore), `exceptions/` |
| application | `application/` | `retrieval/retrieve.py`, `generation/answer_question.py`, `citation/citations.py`, `ingestion/`, `evaluation/` |
| infrastructure | `infrastructure/` | `llm/gemini/gemini_llm.py`, `embeddings/gemini_embedder.py`, `vector_store/chromadb/chroma_store.py`, `chunking/`, `parsing/`, `persistence/` (SQLite cache, JSONL store) |
| presentation | `presentation/desktop/` | `app.py`, `windows/main_window.py`, `viewmodels/`, `workers.py`, `wiring.py` |
| (ngoài lớp) | `config.py`, `composition.py`, `scripts/` | cài đặt và "nơi lắp ráp" (xem 2.2) |

### 1.3 ADR (Architecture Decision Record) — sổ nhật ký quyết định
- **Ý tưởng:** mỗi quyết định kiến trúc quan trọng ghi thành một file ngắn: bối cảnh → quyết định → hệ quả; sửa đổi ghi thành **amendment** có ngày, không xoá lịch sử.
- **C# analogy:** không có tương đương chuẩn; giống "design doc" nhưng bất biến hơn.
- **Trong repo này** (5 ADR ở `docs/architecture/decisions/`):
  | ADR | Quyết định chính | Thấy trong code |
  |---|---|---|
  | 0001 | Quyết định khởi tạo (SETUP-001) | cấu trúc thư mục |
  | 0002 | MarkItDown chỉ nằm trong `infrastructure/parsing/`; chunking header-aware là baseline | [REPO src/knowledge_assistant/infrastructure/parsing/markitdown_parser.py:1-10] |
  | 0003 | D1–D9: normalize, tách H2/H3, 1 600 ký tự, overlap 200, 2 arm A/B, ID chunk | [REPO config/chunking.json:1-21] |
  | 0004 | D10–D13: chọn model Gemini, retry, fallback | [REPO src/knowledge_assistant/config.py:136-155] |
  | 0005 | D14–D19: dim 768, batch 45, cache SQLite, Chroma path, cosine, kế hoạch quota | [REPO src/knowledge_assistant/config.py:57-68] |
- **Tại sao:** dự án do AI agent làm theo từng task; ADR là "trí nhớ" chung. Người review có thể hỏi: "quyết định này dựa trên bằng chứng nào?" và tìm thấy (ví dụ ADR-0005 có bảng đo V-1).
- **Pitfalls:** `[REAL]` ADR có thể bị amendment: ADR-0005 đã sửa hai lần sau verify (F1/F2 và Amendment 2). Đọc **cả phần amendment**, không chỉ đoạn đầu. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:109-129]

---

## Level 2 — Intermediate

### 2.1 Ports & adapters: `Protocol` là "cổng", class trong infrastructure là "bộ chuyển đổi"
- **Ý tưởng:** *port* = interface do lớp trong định nghĩa ("tôi cần thứ có thể tìm vector gần nhất"); *adapter* = class ngoài cùng cài đặt bằng công nghệ cụ thể (Chroma). Lớp trong chỉ thấy port.
- **C# analogy:** `IVectorStore` (Application) và `ChromaVectorStore : IVectorStore` (Infrastructure); DI cắm vào.
- **Trong repo này:** port:
**`src/knowledge_assistant/core/interfaces/vector_store.py:6-19`**
```python
class VectorStore(Protocol):
    """One collection of chunk vectors (one per experiment arm, ADR-0003 D7)."""

    def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        """Insert or replace chunks by `chunk_id`; `embeddings[i]` belongs to `chunks[i]`."""
        ...

    def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        """The `top_k` most similar chunks, rank 1 first."""
        ...

    def count(self) -> int: ...

    def get_ids(self) -> set[str]: ...
```
  và adapter (một class, không ghi "implements" — thoả `Protocol` theo cấu trúc, xem 01 §2.2):
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
  Cùng mẫu cho `LLM` ([REPO src/knowledge_assistant/core/interfaces/llm.py:36-37]) và `Embedder` ([REPO src/knowledge_assistant/core/interfaces/embedding.py:12-18]).
- **Tại sao:** `Retriever` chỉ nhận `VectorStore`, nên test dùng store giả; hệ thống thật dùng Chroma.
- **Pitfalls:** `[REAL]` rò rỉ chi tiết công nghệ vào port là lỗi hay gặp. Ở RAG-001a verify, `plan_calls` (cách chia batch của Gemini) đã lỡ nằm trong `Embedder` của core; ADR-0005 Amendment 2 chuyển nó ra `PlannedEmbedder` trong infrastructure vì "how texts are split into provider calls is a Gemini batching detail". [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:123]

### 2.2 Decorator pattern trên port: `CachingEmbedder` bọc mọi `Embedder`
- **Ý tưởng:** một class vừa **cài** interface vừa **chứa** một đối tượng cùng interface, thêm hành vi (cache) rồi chuyển tiếp.
- **C# analogy:** decorator pattern trong DI (`services.Decorate<IEmbedder, CachingEmbedder>()` của Scrutor).
- **Trong repo này:**
**`src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:56-75`**
```python
class CachingEmbedder:
    """Looks every text up first; only misses reach the inner embedder, one planned call at a time.

    Satisfies the core `Embedder` protocol (`model_id`, `embed`).
    """

    def __init__(self, inner: PlannedEmbedder, path: str | Path) -> None:
        self._inner = inner
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.execute(SCHEMA)
        self._db.commit()
        self.hits = 0  # unique texts served from the cache
        self.misses = 0  # unique texts sent to the inner embedder
        self.inner_calls = 0
        self.estimated_tokens = 0  # of the misses

    @property
    def model_id(self) -> str:
        return self._inner.model_id
```
  `CachingEmbedder` nhận `inner` (một `PlannedEmbedder`) và tự nó thoả `Embedder` (có `model_id` và `embed`). Nhờ vậy application nhận nó như một `Embedder` thường. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:123]
- **Tại sao:** cache là mối quan tâm hạ tầng; use case không cần biết.
- **Pitfalls:** `[GENERAL]` decorator che dấu chi phí thật; repo bù bằng bộ đếm `hits/misses/inner_calls/stats()` ([REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:68-87]).

### 2.3 Composition root — nơi duy nhất "lắp" các mảnh với nhau
- **Ý tưởng:** một chỗ tạo các đối tượng cụ thể (Gemini, Chroma, cache), nối chúng vào use case. Mọi nơi khác chỉ nhận dependency qua constructor.
- **C# analogy:** `Program.cs` với `builder.Services.AddSingleton<...>()`, nhưng **thủ công** (không dùng DI container). Ở đây là hàm `build_answer_service`.
- **Trong repo này:**
**`src/knowledge_assistant/composition.py:1-5`**
```python
"""Composition root: wires the layers for scripts (ask, smoke checks) and, later, the GUI and the eval runner.

The one module besides the scripts that names both application and infrastructure classes. Everything here is
plumbing: settings in, a ready `AnswerQuestion` out; no business rule lives here.
"""
```
**`src/knowledge_assistant/composition.py:58-77`**
```python
def build_answer_service(
    arm: str,
    llm: LLM,
    embedder: Embedder,
    *,
    store: VectorStore | None = None,
    gate_off: bool = False,
) -> AnswerQuestion:
    """One `AnswerQuestion` for one arm. `gate_off=True` disables the retrieval gate so a low-scoring question still
    reaches the LLM: a diagnostic for checking the LLM's own "insufficient" path, never used for evaluation."""
    answer = get_answer_settings()
    retrieval = get_retrieval_settings()
    threshold = float("-inf") if gate_off else retrieval.insufficient_score_threshold
    return AnswerQuestion(
        Retriever(embedder, store or open_vector_store(arm), retrieval.top_k, retrieval.overfetch),
        llm,
        PromptBuilder.from_dir(answer.prompts_dir, answer.prompt_version),
        load_messages(answer.messages_path),
        threshold,
    )
```
  Đọc: chọn cài đặt, tạo `Retriever(embedder, store, top_k, overfetch)`, `PromptBuilder` từ file prompt, đọc thông điệp từ config, ngưỡng gate; trả `AnswerQuestion`. `gate_off=True` đặt ngưỡng `-inf` — chế độ chẩn đoán, **không** dùng khi đánh giá (docstring).
  Ngoài `composition.py`, các script (`scripts/ask.py`) cũng là điểm vào; `wiring.py` là "cửa" của GUI (xem 3.3).
- **Tại sao:** dễ biết "ai tạo cái gì"; test có thể dựng use case với fake mà không đụng file này.
- **Pitfalls:** `[GENERAL]` nếu composition root phình ra chứa logic nghiệp vụ, kiến trúc hỏng; docstring nhắc "no business rule lives here".

### 2.4 Error boundary: exception của nhà cung cấp không rời khỏi infrastructure
- **Ý tưởng:** lỗi của SDK (`google.genai.errors`, `httpx`) bị **bắt và dịch** thành exception của core (`LLMQuotaError`, ...). Lớp trên chỉ biết exception domain.
- **C# analogy:** anti-corruption layer; bắt `HttpRequestException` rồi ném `DomainException`.
- **Trong repo này:**
**`src/knowledge_assistant/infrastructure/gemini_retry.py:1-6`**
```python
"""Retry, retry-after, quota classification and key redaction shared by the Gemini embedder and the Gemini LLM adapter.

Moved out of gemini_embedder.py (RAG-003, ADR-0004 amendment 2026-09-26) so both adapters retry and classify errors
the same way. `classify_failure` is the only place that knows which google.genai / httpx exceptions are provider
failures; an adapter turns a `Failure` into its own core error type, so no such exception leaves infrastructure.
"""
```
  Rồi GUI adapter dịch tiếp thành mã hiển thị:
**`src/knowledge_assistant/presentation/desktop/viewmodels/core_ask_question.py:43-51`**
```python
def to_gui_error(error: Exception) -> AskQuestionError:
    """LLMError.kind is the GUI kind 1:1; a missing/empty index is no_index; everything else is other."""
    if isinstance(error, LLMError):
        kind = error.kind
    elif isinstance(error, (RetrievalError, VectorStoreError)):
        kind = "no_index"
    else:
        kind = "other"
    return AskQuestionError(kind, str(error))
```
  Chú ý `LLMError.kind` được thiết kế **1:1** với `AskQuestionError.kind` của GUI ([REPO src/knowledge_assistant/core/exceptions/__init__.py:41-50]).
- **Tại sao:** GUI không cần (và không được) cài `google-genai`; test kiểm điều này:
**`tests/unit/test_project_structure.py:37-39`**
```python
def test_presentation_does_not_import_provider_libraries():
    """RAG-003: google.genai / httpx exceptions are wrapped in infrastructure, so the GUI never needs (or sees) them."""
    assert not _imports("presentation") & {"google", "httpx", "chromadb", "markitdown"}
```
- **Pitfalls:** `[REAL]` RAG-003: trước khi có boundary, lỗi kết nối `httpx.ConnectError` có thể lọt ra ngoài; sau đó được bọc thành `EmbeddingError`/`LLMError`. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:127]

### 2.5 Architecture test: luật kiến trúc được kiểm bằng code
- **Ý tưởng:** test dùng module `ast` (Abstract Syntax Tree) để **đọc** mọi file `.py` của một lớp, gom danh sách `import`, rồi khẳng định không có import cấm. Không chạy code, chỉ phân tích cú pháp.
- **C# analogy:** thư viện **ArchUnitNET** / NetArchTest ("types in `Core` should not depend on `Infrastructure`").
- **Trong repo này:**
**`tests/unit/test_project_structure.py:11-19`**
```python
def _imports(layer: str) -> set[str]:
    found = set()
    for py in (PKG / layer).rglob("*.py"):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                found.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                found.add(node.module.split(".")[0])
    return found
```
**`tests/unit/test_project_structure.py:28-34`**
```python
def test_core_has_no_technology_dependencies():
    assert not _imports("core") & set(FORBIDDEN_CORE)


def test_application_has_no_technology_or_presentation_dependencies():
    assert not _imports("application") & set(FORBIDDEN_APP)
    assert "presentation" not in _imports("application")
```
  Test cuối cùng ghim rằng chỉ `wiring.py` được chạm composition/infrastructure trong presentation:
**`tests/unit/test_project_structure.py:73-83`**
```python
def test_only_the_desktop_wiring_touches_composition_and_infrastructure():
    """GUI-001: view-model, view, adapter and fake stay clean; `wiring.py` is the one seam to the composition root."""
    importers = set()
    for py in (PKG / "presentation").rglob("*.py"):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            if any(n.startswith(("knowledge_assistant.composition", "knowledge_assistant.infrastructure")) for n in names):
                importers.add(py.relative_to(PKG).as_posix())
    assert importers == {"presentation/desktop/wiring.py"}
```
- **Tại sao:** luật nằm trong CLAUDE.md sẽ bị vi phạm dần nếu không có gì canh; test biến luật thành thứ **fail được**.
- **Đã chạy thử offline** (bản sao ở thư mục tạm, repo không bị sửa): 9 test đều pass ở commit gốc; thêm `import chromadb` vào đầu `core/models/__init__.py` → `test_core_has_no_technology_dependencies` **fail**; thêm `from knowledge_assistant.infrastructure... import ...` vào `application/common/passage.py` → `test_core_and_application_do_not_import_outer_layers` **fail**.
- **Pitfalls:** `[GENERAL]` test chỉ thấy import dạng `import x`/`from x import y`; import động (`importlib`) bằng chuỗi sẽ lọt. Cũng vậy, `registry.default_registry()` cố ý import MarkItDown **bên trong hàm** để tránh nạp thư viện nặng khi không cần ([REPO src/knowledge_assistant/infrastructure/parsing/registry.py:20-31]) — nhưng vẫn nằm trong infrastructure nên hợp lệ.

### 2.6 Domain model độc lập định dạng (format-independent)
- **Ý tưởng:** `Document`, `ParsedDocument`, `DocumentChunk`, `Citation` không biết file gốc là PDF hay Markdown. Parser đưa mọi thứ về **văn bản Markdown**; chỉ chunker (infrastructure) mới "hiểu" Markdown. Vị trí trích dẫn là **heading path**, không bao giờ là số trang.
- **Trong repo này:**
**`src/knowledge_assistant/core/models/__init__.py:48-64`**
```python
@dataclass(frozen=True)
class DocumentChunk:
    """Exactly the ADR-0003 D6 fields."""

    chunk_id: str  # {source_id}:{chunker_config}:{index:04d}
    source_id: str
    document_name: str
    source_url: str | None
    heading_path: tuple[str, ...]
    location_type: str
    char_start: int  # offsets into the normalized text
    char_end: int
    display_text: str
    embed_text: str
    content_hash: str
    chunker_config: str

```
  `char_start/char_end` là offset vào văn bản đã chuẩn hoá; `display_text` (cái người dùng thấy) khác `embed_text` (cái đưa vào embedding, có dòng heading path ở đầu).
- **Tại sao:** ADR-0002 và ADR-0003 D5/D6; cho phép thêm PDF/HTML sau này mà không đổi core.
- **Pitfalls:** `[GENERAL]` "location" bằng heading path không phân biệt được hai section trùng tên; repo đánh số biến thể (`variant`) khi trùng heading path ([REPO src/knowledge_assistant/core/models/__init__.py:20-28]).

---

## Level 3 — Advanced

### 3.1 MVVM trong GUI: View ↔ ViewModel ↔ Port
- **Ý tưởng:** MVVM tách **View** (widget, chỉ hiển thị), **ViewModel** (state + lệnh, **không** biết Qt), và **Model/Port** (gọi use case). ViewModel thông báo thay đổi qua callback (`subscribe`).
- **C# analogy:** WPF/MAUI MVVM: `INotifyPropertyChanged` ↔ `_notify()` và danh sách listener; `ICommand` ↔ method `submit`.
- **Trong repo này:** trạng thái là một `Enum` (máy trạng thái nhỏ), view-model chỉ Python thuần:
**`src/knowledge_assistant/presentation/desktop/viewmodels/ask_viewmodel.py:31-49`**
```python
class ViewState(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ANSWER = "answer"
    INSUFFICIENT = "insufficient"
    ERROR = "error"


class AskViewModel:
    def __init__(self, port: AskQuestionPort, executor: Executor) -> None:
        self._port = port
        self._executor = executor
        self._listeners: list[Callable[[], None]] = []
        self.state = ViewState.IDLE
        self.arm = ARMS[0]
        self.result: AnswerResult | None = None
        self.error_title = ""
        self.error_message = ""
        self.selected: Citation | None = None
```
**`src/knowledge_assistant/presentation/desktop/viewmodels/ask_viewmodel.py:51-56`**
```python
    def subscribe(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def _notify(self) -> None:
        for listener in self._listeners:
            listener()
```
  Lệnh `submit`:
**`src/knowledge_assistant/presentation/desktop/viewmodels/ask_viewmodel.py:67-75`**
```python
    def submit(self, question: str) -> None:
        if not self.can_submit(question):
            return
        question = question.strip()
        arm = self.arm
        self.state = ViewState.BUSY
        self.result, self.selected, self.error_message = None, None, ""
        self._notify()
        self._executor(lambda: self._port.ask(question, arm), self._on_ok, self._on_err)
```
  Đọc: nếu không được phép gửi (rỗng hoặc đang BUSY) → thôi; đặt trạng thái BUSY, xoá kết quả cũ, báo view; rồi **giao việc cho `executor`** với hai callback `_on_ok`/`_on_err`. `lambda: self._port.ask(question, arm)` là "việc cần làm" (một hàm không tham số).
  View chỉ vẽ theo state, không có luật nghiệp vụ ([REPO src/knowledge_assistant/presentation/desktop/windows/main_window.py:1]).
- **Tại sao:** view-model test được **không cần Qt** và không cần vòng lặp sự kiện: docstring đầu file ghi rõ ([REPO src/knowledge_assistant/presentation/desktop/viewmodels/ask_viewmodel.py:1-5]). Test dùng executor đồng bộ:
**`tests/presentation/desktop/test_ask_viewmodel.py:8-18`**
```python
def sync_executor(fn, on_ok, on_err):
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001
        on_err(exc)
    else:
        on_ok(result)


def make_vm(executor=sync_executor):
    return AskViewModel(FakeAskQuestion(sleep=lambda s: None), executor)
```
- **Pitfalls:** `[GENERAL]` quên thông báo view sau khi đổi state → giao diện không cập nhật; mọi chỗ đổi state ở đây đều kết thúc bằng `self._notify()`.

### 3.2 Chạy việc nặng ngoài luồng GUI: `QThreadPool`, `QRunnable`, `Signal`
- **Ý tưởng:** gọi Gemini mất hàng giây; nếu làm trên luồng GUI thì cửa sổ "đơ". Ta đưa việc vào **thread pool**. Nhưng widget/Qt object chỉ được đụng từ luồng GUI, nên kết quả phải **quay về luồng GUI** qua `Signal` (Qt tự xếp hàng — *queued connection* — khi signal phát từ luồng khác).
- **C# analogy:** `Task.Run(work)` rồi `await` quay về UI thread; hoặc `Dispatcher.Invoke`/`SynchronizationContext.Post`. `QRunnable` ≈ đơn vị công việc cho `ThreadPool`; `Signal` ≈ event có marshaling luồng.
- **Trong repo này:**
**`src/knowledge_assistant/presentation/desktop/workers.py:10-20`**
```python
class _Job(QRunnable):
    def __init__(self, job_id: int, fn: Callable[[], object], owner: "QtExecutor") -> None:
        super().__init__()
        self._id, self._fn, self._owner = job_id, fn, owner

    def run(self) -> None:
        try:
            self._owner._finished.emit(self._id, self._fn(), None)
        except Exception as exc:  # noqa: BLE001 - forwarded to the view-model
            self._owner._finished.emit(self._id, None, exc)

```
**`src/knowledge_assistant/presentation/desktop/workers.py:22-42`**
```python
class QtExecutor(QObject):
    """Must be created on the GUI thread; its signal is delivered there (queued) from the worker."""

    _finished = Signal(int, object, object)

    def __init__(self, pool: QThreadPool | None = None) -> None:
        super().__init__()
        self._pool = pool or QThreadPool.globalInstance()
        self._ids = itertools.count()
        self._pending: dict[int, tuple[Callable, Callable]] = {}
        self._finished.connect(self._deliver)

    def __call__(self, fn, on_ok, on_err) -> None:
        job_id = next(self._ids)
        self._pending[job_id] = (on_ok, on_err)
        self._pool.start(_Job(job_id, fn, self))

    @Slot(int, object, object)
    def _deliver(self, job_id: int, result: object, exc: object) -> None:
        on_ok, on_err = self._pending.pop(job_id)
        (on_err(exc) if exc is not None else on_ok(result))
```
  Đọc: `__call__(fn, on_ok, on_err)` lưu cặp callback theo `job_id`, đưa `_Job` vào pool. `_Job.run` chạy trên **worker thread**, chạy `fn()`, rồi phát `_finished` (kết quả hoặc exception). `_deliver` được nối với signal đó và (vì `QtExecutor` được tạo ở luồng GUI) chạy trên **luồng GUI**, lấy callback ra và gọi. `# noqa: BLE001` nói: bắt `Exception` rộng là cố ý, được chuyển cho view-model.
  `AskViewModel` nhận `executor` qua constructor; `app.py` truyền `QtExecutor(QThreadPool())`, test truyền hàm đồng bộ. [REPO src/knowledge_assistant/presentation/desktop/app.py:34-36]
- **Tại sao:** ViewModel không biết Qt; chỉ biết "một `executor(fn, on_ok, on_err)`". Đổi cách chạy nền không đụng ViewModel.
- **Pitfalls:** `[GENERAL]` đụng widget từ worker thread gây crash khó tái hiện; luôn quay về luồng GUI như trên.

### 3.3 Thread affinity và state dùng chung: `PerCallEmbedder`, `Lock`, lazy service
- **Ý tưởng:** cache embedding là kết nối SQLite — chỉ dùng được trên luồng đã tạo ra nó — trong khi pool chạy mỗi câu hỏi trên worker rảnh bất kỳ. Giải pháp: **mở cache cho từng lần gọi** rồi đóng.
- **Trong repo này:**
**`src/knowledge_assistant/presentation/desktop/wiring.py:27-51`**
```python
class PerCallEmbedder:
    """Query embedder that opens the cached embedder for each call and closes it again.

    The embedding cache is a SQLite connection, which may only be used by the thread that created it, while the
    thread pool runs each question on whichever worker is free. Opening per call is safe on any thread and costs
    one file open (a cached query text still spends no request).
    """

    @property
    def model_id(self) -> str:
        return get_embedding_settings().model_id

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        with open_embedder() as embedder:
            return embedder.embed(texts, task)


def build_real_port() -> CoreAskQuestion:
    llm = GeminiLLM(replace(get_answer_settings(), allow_fallback=True))
    embedder = PerCallEmbedder()

    def service_for_arm(arm: str) -> AnswerQuestion:
        return build_answer_service(arm, llm, embedder)

    return CoreAskQuestion(service_for_arm)
```
  Và service theo từng arm được dựng lười (lần dùng đầu) dưới `Lock` để không dựng hai lần:
**`src/knowledge_assistant/presentation/desktop/viewmodels/core_ask_question.py:54-72`**
```python
class CoreAskQuestion:
    def __init__(self, service_for_arm: Callable[[str], _Service]) -> None:
        self._factory = service_for_arm
        self._services: dict[str, _Service] = {}
        self._lock = threading.Lock()

    def _service(self, arm: str) -> _Service:
        with self._lock:  # built on the worker thread on first use; never twice
            if arm not in self._services:
                self._services[arm] = self._factory(arm)
            return self._services[arm]

    def ask(self, question: str, arm: str) -> AnswerResult:
        try:
            return to_gui_result(self._service(arm).ask(question))
        except AskQuestionError:
            raise
        except Exception as error:
            raise to_gui_error(error) from error
```
- **Tại sao:** một `GeminiLLM` chung cho cả 2 arm để **chia sẻ throttle** (bảng RPM); cửa sổ mở được ngay cả khi thiếu index (lỗi hiện khi hỏi câu đầu). `allow_fallback=True` bị ép ở đây: app dùng model dự phòng khi model chính lỗi; runner đánh giá làm ngược lại (docstring wiring). [REPO src/knowledge_assistant/presentation/desktop/wiring.py:9-12]
- **Pitfalls:** `[GENERAL]` `with self._lock:` kiểm tra-rồi-tạo là mẫu chống race; nếu thiếu lock, hai worker cùng thấy "chưa có" và tạo hai lần.

### 3.4 Contract GUI riêng + một adapter map duy nhất
- **Ý tưởng:** GUI có **kiểu riêng** (`contracts.AnswerResult`, `Citation`) gần giống model core, nhưng tách rời; đúng một chỗ (`to_gui_result`) map từ core sang GUI.
- **Trong repo này:**
**`src/knowledge_assistant/presentation/desktop/viewmodels/core_ask_question.py:23-40`**
```python
def to_gui_result(result: CoreAnswerResult) -> AnswerResult:
    llm = result.llm  # None when the retrieval gate answered (no model call)
    return AnswerResult(
        question=result.question,
        language=result.language,
        answer=result.answer,
        insufficient=result.insufficient,
        insufficient_reason=result.insufficient_reason,
        missing_information=result.missing_information,
        citations=tuple(
            # D2: every citation of an insufficient answer is related content, not the answer (mismatch 1)
            Citation(c.marker, c.document_name, c.location, c.excerpt, c.source_url, related_only=result.insufficient)
            for c in result.citations
        ),
        latency_ms=dict(result.latency_ms),  # no "generate" key when the gate answered (mismatch 5): nothing invented
        model_used=llm.model_used if llm else None,
        fallback_used=bool(llm and llm.fallback_used),
    )
```
  `related_only=result.insufficient` mã hoá quy tắc D2: mọi citation của câu trả lời "không đủ thông tin" chỉ là nội dung **liên quan**, không phải bằng chứng cho câu trả lời.
- **Tại sao:** đổi `AnswerResult` core không phá GUI (chỉ sửa `to_gui_result`). `contracts.py` là "file DUY NHẤT trong presentation biết hình dạng câu trả lời" ([REPO src/knowledge_assistant/presentation/desktop/viewmodels/contracts.py:1-6]).
- **Pitfalls:** `[GENERAL]` trùng lặp kiểu là cái giá; đổi lại là ranh giới rõ ràng.

### 3.5 Import lười và chế độ `--fake`
- **Trong repo này:**
**`src/knowledge_assistant/presentation/desktop/app.py:15-39`**
```python
    from PySide6.QtCore import QThreadPool
    from PySide6.QtWidgets import QApplication

    from .viewmodels.ask_viewmodel import AskViewModel
    from .windows.main_window import MainWindow
    from .workers import QtExecutor

    if fake:
        from .viewmodels.fake_ask_question import FakeAskQuestion

        port = FakeAskQuestion()
    else:
        from dotenv import load_dotenv

        from .wiring import build_real_port

        load_dotenv(Path(__file__).resolve().parents[4] / ".env")
        port = build_real_port()

    app = QApplication(sys.argv[:1])
    # one question at a time (the view-model disables input while busy); a private pool keeps the global one free
    vm = AskViewModel(port, QtExecutor(QThreadPool()))
    window = MainWindow(vm, title="Knowledge Assistant (fake data)" if fake else "Knowledge Assistant")
    window.show()
    return app.exec()
```
  `PySide6` chỉ được import **trong hàm** `main` để việc import package không đòi hỏi PySide6 (docstring). `--fake` dùng `FakeAskQuestion` để chạy GUI hoàn toàn offline/không key. `app.exec()` chạy vòng lặp sự kiện Qt.
- **Tại sao:** demo và kiểm tra giao diện không tốn quota; test khởi tạo được không cần màn hình thật (xem test smoke ở `tests/presentation/desktop/`).
- **Pitfalls:** `[GENERAL]` import trong hàm che giấu phụ thuộc; ở đây được chấp nhận vì có docstring và test.

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Cho các import sau; mỗi cái có được phép **trong `core/`** không? (a) `from dataclasses import dataclass` (b) `import chromadb` (c) `from knowledge_assistant.core.exceptions import LLMError` (d) `from knowledge_assistant.infrastructure.gemini_retry import redact_key`.
<details><summary>Đáp án</summary>
(a) Được (stdlib). (b) **Không** — `chromadb` nằm trong `FORBIDDEN_CORE` ([REPO tests/unit/test_project_structure.py:7]). (c) Được (cùng lớp core). (d) **Không** — core/application không được import `knowledge_assistant.infrastructure` ([REPO tests/unit/test_project_structure.py:42-47]).
</details>

**B2 (Basic).** Vì sao `LLM` được định nghĩa trong `core/interfaces/llm.py` mà `GeminiLLM` nằm trong `infrastructure/llm/gemini/`?
<details><summary>Đáp án</summary>
Interface (port) thuộc lớp trong để use case phụ thuộc vào nó; cài đặt cụ thể (adapter) thuộc lớp ngoài để công nghệ Gemini bị cô lập. Đổi nhà cung cấp chỉ cần adapter mới ([REPO CLAUDE.md:10], rule 6).
</details>

**I1 (Intermediate).** Chạy `.venv/Scripts/python.exe -m pytest tests/unit/test_project_structure.py -q` (offline). Bao nhiêu test pass? Test nào cấm GUI import `google`/`httpx`?
<details><summary>Đáp án</summary>
Ở commit này: `9 passed` (đã chạy). `test_presentation_does_not_import_provider_libraries` cấm `{"google","httpx","chromadb","markitdown"}` trong presentation ([REPO tests/unit/test_project_structure.py:37-39]).
</details>

**I2 (Intermediate).** Đọc `build_answer_service`. Ai cung cấp `store` nếu bạn không truyền? Nó tạo collection mới hay mở collection có sẵn?
<details><summary>Đáp án</summary>
`store or open_vector_store(arm)` (dòng 72). `open_vector_store` mở collection **đã có** ("never creates one"): nếu thiếu file chunk hoặc collection chưa tồn tại thì ném `VectorStoreError` kèm hướng dẫn chạy script build ([REPO src/knowledge_assistant/composition.py:42-55]).
</details>

**I3 (Intermediate).** `LLMQuotaError` ánh xạ sang `AskQuestionError.kind` nào? `RetrievalError`? Một `ValueError` bất kỳ?
<details><summary>Đáp án</summary>
`LLMQuotaError.kind == "quota"` → `"quota"`; `RetrievalError` (và `VectorStoreError`) → `"no_index"`; mọi thứ khác → `"other"` ([REPO src/knowledge_assistant/presentation/desktop/viewmodels/core_ask_question.py:43-51]).
</details>

**A1 (Advanced).** Vẽ (chữ) luồng khi người dùng bấm "Ask": nêu luồng nào chạy từng bước — `submit`, `executor.__call__`, `_Job.run`, `CoreAskQuestion.ask`, `_deliver`, `_on_ok`.
<details><summary>Đáp án</summary>
GUI thread: `submit` (BUSY, notify) → `QtExecutor.__call__` (lưu callback, `pool.start`). **Worker thread:** `_Job.run` → `fn()` = `port.ask(question, arm)` → `CoreAskQuestion.ask` → use case core (embed, search, LLM…). Worker phát `_finished(id, result, exc)`. **GUI thread** (queued): `_deliver` → `on_ok(result)` = `_on_ok` (đổi state ANSWER/INSUFFICIENT, notify). Nếu có lỗi: `on_err` = `_on_err` (state ERROR).
</details>

**A2 (Advanced).** Thí nghiệm tư duy: nếu `PerCallEmbedder` giữ **một** `CachingEmbedder` dùng chung cho mọi câu hỏi thì có thể sai ở đâu? Tại sao repo không làm vậy?
<details><summary>Đáp án</summary>
`CachingEmbedder` giữ một kết nối `sqlite3` tạo ở một luồng; pool chạy câu hỏi trên luồng bất kỳ → SQLite mặc định chỉ cho dùng connection trên luồng tạo ra nó ("may only be used by the thread that created it", docstring [REPO src/knowledge_assistant/presentation/desktop/wiring.py:30-32]). Mở-đóng theo từng lần gọi chỉ tốn một lần mở file, và văn bản đã cache vẫn không tốn request.
</details>

## Self-check questions
1. Dependency rule nói gì? Mũi tên chỉ hướng nào?
2. Port khác adapter thế nào? Cho ví dụ từ repo.
3. Composition root là gì và vì sao chỉ có một chỗ?
4. Vì sao exception của Gemini không được ra khỏi `infrastructure`?
5. Architecture test hoạt động ra sao (nói được chữ `ast`)?
6. Vì sao view-model không import Qt?
7. Vì sao kết quả từ worker phải quay về GUI thread qua `Signal`?

## Interview Q&A
1. **"Clean architecture ở dự án này khác project reference của .NET ở điểm nào?"** — Không có compiler ép; luật được canh bằng test `ast` ([REPO tests/unit/test_project_structure.py:11-19]).
2. **"Kể một lần thiết kế port bị rò rỉ chi tiết công nghệ?"** — `plan_calls` (batching của Gemini) nằm trong `Embedder` core; ADR-0005 Amendment 2 chuyển sang `PlannedEmbedder` ([REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:123]).
3. **"Làm thế nào test được code gọi LLM mà không tốn quota?"** — `LLM` là `Protocol`; test truyền `FakeLLM`/`ScriptedLLM` ([REPO tests/fakes.py:187]).
4. **"MVVM ở đây khác WPF thế nào?"** — Không có data binding: view-model phát `_notify()` tới listener; view vẽ lại. Đổi lại, view-model test được không cần Qt.
5. **"Vì sao dùng `Lock` trong `CoreAskQuestion._service`?"** — Service theo arm dựng lười trên worker thread; lock chặn dựng hai lần ([REPO src/knowledge_assistant/presentation/desktop/viewmodels/core_ask_question.py:60-64]).

## Further reading
- Robert C. Martin, *Clean Architecture* (khái niệm dependency rule); Alistair Cockburn, *Hexagonal Architecture (Ports and Adapters)*. `[GENERAL]`
- Python docs: `typing.Protocol`, `ast`. Qt for Python docs: *QThreadPool*, *QRunnable*, *Signals & Slots* (doc.qt.io/qtforpython-6). `[GENERAL]`
- Tiếp theo: [05 — RAG fundamentals](05-rag-fundamentals.md).
