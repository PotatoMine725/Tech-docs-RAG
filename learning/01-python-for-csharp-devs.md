# 01 · Python cho dev C#: cú pháp và idiom có thật trong repo này
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: biết C#/.NET cơ bản · Study time: ~8–10h · Home file của: cú pháp & idiom Python (mọi file khác link về đây)
> Ký hiệu: `[REPO path:line]` = đã kiểm tra trong repo · `[GENERAL]` = kiến thức chung · `[REAL]` = sự cố thật của dự án này (nguồn kèm theo).
> File đi kèm: [01b — Hướng dẫn đọc code Python](01b-python-code-reading-guide.md) (bảng giải mã ký hiệu + template để **đọc hiểu** code).

## Vì sao file này quan trọng trong dự án
Toàn bộ dự án là Python (~6 470 dòng trong `src/`), và bạn đến từ C#/.NET. Mục tiêu của file này **không phải** là dạy toàn bộ Python, mà là dạy đúng những cú pháp/idiom mà repo này dùng, theo thứ tự "cái sau chỉ dựa vào cái trước". Sau file này bạn sẽ đọc được `src/knowledge_assistant/` mà không bị vấp ở cú pháp, để dành sức cho phần khó thật sự (RAG, retry, thống kê).

Cách đọc: mỗi khái niệm có đúng 5 phần — **Ý tưởng**, **Tương đương C#**, **Trong repo này** (snippet nguyên văn), **Tại sao làm vậy**, **Pitfalls**.

---

## Level 1 — Basic

### 1.1 Module, package, `import`
- **Ý tưởng:** Một file `.py` là một *module*; một thư mục có `__init__.py` là một *package*. `import` nạp module (chạy code cấp cao nhất của nó **một lần**). `from x import y` lấy tên `y` vào namespace hiện tại.
- **C# analogy:** file ≈ một `static class`/file `.cs`; package ≈ namespace + thư mục; `import` ≈ `using` **nhưng** có thực thi code (top-level code chạy lúc import). Không có `public`/`internal`: mọi tên đều truy cập được, quy ước `_ten` = "nội bộ" (không bị ép buộc).
- **Trong repo này:**
**`src/knowledge_assistant/config.py:1-15`**
```python
import os
from dataclasses import dataclass
from pathlib import Path

from knowledge_assistant.core.exceptions import ConfigurationError

# src/knowledge_assistant/config.py -> repo root. Relative paths resolve from here, never from the cwd,
# so a script started in another directory reads and writes the same files (ADR-0005 D16).
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(value: str | Path) -> Path:
    """A relative path (default or env value) is taken from the repo root; an absolute one is kept."""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path
```
  Ở đây `PROJECT_ROOT = Path(__file__).resolve().parents[2]` dùng biến đặc biệt `__file__` (đường dẫn file hiện tại). Đọc từ trái sang phải: file này → tuyệt đối hoá → đi lên 2 cấp thư mục = gốc repo.
- **Tại sao:** đường dẫn tương đối luôn tính từ gốc repo, **không** từ thư mục đang đứng (ADR-0005 D16). Nhờ vậy chạy script từ đâu cũng đọc đúng file. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:66]
- **Pitfalls:** `[GENERAL]` import vòng (A import B, B import A) gây lỗi khó hiểu; repo tránh bằng luật layer (xem file 03). `[GENERAL]` khác C#, thứ tự `import` có thể quan trọng vì code chạy lúc import.

### 1.2 Type hint chỉ là chú thích, không bị ép lúc chạy
- **Ý tưởng:** `def f(value: str | Path) -> Path:` nói "value là str hoặc Path, trả về Path". Python **không kiểm tra** khi chạy; công cụ như mypy/IDE mới kiểm tra. `X | None` ≈ "có thể null".
- **C# analogy:** giống `string?` / `T?` (nullable reference types) nhưng chỉ là gợi ý; C# compiler chặn, Python thì không. `list[str]` ≈ `List<string>`, `dict[str, int]` ≈ `Dictionary<string,int>`, `tuple[str, ...]` ≈ "tuple độ dài tuỳ ý toàn string" (≈ `IReadOnlyList<string>`).
- **Trong repo này:** [REPO src/knowledge_assistant/config.py:12-15] (`str | Path`), [REPO src/knowledge_assistant/core/models/__init__.py:13-16] (`str | None`).
- **Tại sao:** giúp người đọc (và AI agent) biết hình dạng dữ liệu; không tốn chi phí chạy.
- **Pitfalls:** `[GENERAL]` đừng tin hint như bảo đảm. Repo bù bằng kiểm tra chạy thật ở chỗ quan trọng, ví dụ `parse_answer_json` tự kiểm từng kiểu (xem 2.6).

### 1.3 `@dataclass(frozen=True)` ≈ `record`
- **Ý tưởng:** `@dataclass` sinh sẵn `__init__`, `__eq__`, `__repr__` từ danh sách field. `frozen=True` làm object **bất biến** (gán field sau khi tạo sẽ lỗi).
- **C# analogy:** `public record Document(string SourceId, string Name, ...)` hoặc `readonly record struct`. Cả hai cho value-equality và immutability.
- **Trong repo này:** (47 chỗ dùng `@dataclass(frozen=True)` trong 18 file)
**`src/knowledge_assistant/core/models/__init__.py:9-16`**
```python
@dataclass(frozen=True)
class Document:
    """A source document to ingest (format-independent reference)."""

    source_id: str
    name: str
    path: str = ""
    source_url: str | None = None
```
  Field có giá trị mặc định (`path: str = ""`) phải đứng **sau** field không mặc định (giống tham số optional trong C#).
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
  `@property` biến method thành thuộc tính đọc: `settings.model_id` (không có ngoặc).
- **Tại sao:** dữ liệu chảy giữa các layer là "giá trị", không nên bị sửa lén. Bất biến giúp test và suy luận dễ hơn.
- **Pitfalls:** `[GENERAL]` frozen chỉ chặn gán field, **không** làm list/dict bên trong bất biến. Repo tránh bằng cách dùng `tuple` thay `list` cho field bất biến (ví dụ `heading_path: tuple[str, ...]`, [REPO src/knowledge_assistant/core/models/__init__.py:56]).

### 1.4 Hàm, tham số mặc định, f-string, `os.getenv`
- **Ý tưởng:** tham số có default `def f(a, b=5)`. f-string `f"kb_{name}"` nhúng biểu thức. `os.getenv("X", "default")` đọc biến môi trường.
- **C# analogy:** optional parameter; `$"kb_{name}"`; `Environment.GetEnvironmentVariable`.
- **Trong repo này:**
**`src/knowledge_assistant/config.py:18-35`**
```python
def get_chroma_path() -> Path:
    """OD-7 (ADR-0005): repo-local, git-ignored, rebuilt by script."""
    return resolve_project_path(os.getenv("CHROMA_PATH", "data/chroma"))


def get_chunks_dir() -> Path:
    """Chunk files written by scripts/ingestion/build_chunks.py (arm-a.jsonl, arm-b.jsonl)."""
    return resolve_project_path(os.getenv("CHUNKS_DIR", "data/processed/chunks"))


def get_logs_dir() -> Path:
    """Run logs (indexing, evaluation); git-ignored."""
    return resolve_project_path(os.getenv("LOGS_DIR", "data/logs"))


def get_gemini_api_key() -> str | None:
    """Read the key from the environment only; never log or print it."""
    return os.getenv("GEMINI_API_KEY") or None
```
  Lưu ý `os.getenv("GEMINI_API_KEY") or None`: chuỗi rỗng `""` là "falsy" trong Python, nên `"" or None` → `None`. Đây là idiom "coi chuỗi rỗng như chưa đặt".
- **Tại sao:** mọi cài đặt đổi được bằng biến môi trường, không sửa code; key chỉ đọc từ environment (CLAUDE.md rule 7). Docstring dặn rõ "never log or print it".
- **Pitfalls:** `[GENERAL]` mọi giá trị env đều là **chuỗi** — phải ép kiểu (`int(...)`, `float(...)`) như [REPO src/knowledge_assistant/config.py:59-68].

### 1.5 Bốn kiểu tập hợp: `list`, `dict`, `tuple`, `set`
- **Ý tưởng:** `list` = mảng động; `dict` = từ điển (giữ **thứ tự chèn**); `tuple` = dãy bất biến; `set` = tập không trùng.
- **C# analogy:** `List<T>`, `Dictionary<K,V>` (nhưng Python dict có thứ tự), `ValueTuple`/mảng bất biến, `HashSet<T>`.
- **Trong repo này:**
**`src/knowledge_assistant/application/retrieval/retrieve.py:29-45`**
```python
def dedupe_by_passage(hits: list[RetrievedChunk], top_k: int) -> tuple[list[RetrievedChunk], int]:
    """(the top_k unique-passage hits re-ranked 1..k with `duplicate_chunk_ids`, duplicate hits dropped in `hits`)."""
    ordered = sorted(hits, key=lambda hit: (-hit.score, hit.chunk.chunk_id))
    kept: dict[str, RetrievedChunk] = {}  # passage_hash -> first (best) hit, in rank order
    replaced: dict[str, list[str]] = {}
    for hit in ordered:
        key = passage_hash(hit.chunk)
        if key in kept:
            replaced[key].append(hit.chunk.chunk_id)
        else:
            kept[key] = hit
            replaced[key] = []
    dropped = len(ordered) - len(kept)
    return [
        RetrievedChunk(chunk=hit.chunk, rank=rank, score=hit.score, duplicate_chunk_ids=tuple(replaced[key]))
        for rank, (key, hit) in enumerate(list(kept.items())[:top_k], start=1)
    ], dropped
```
  Đọc chậm: (1) `sorted(hits, key=lambda hit: (-hit.score, hit.chunk.chunk_id))` sắp giảm dần theo score, hoà thì theo `chunk_id` (dùng **tuple** làm khoá so sánh; dấu `-` để đảo chiều số). (2) `kept: dict[str, RetrievedChunk] = {}` là dict "passage_hash → hit tốt nhất", dựa vào việc dict giữ thứ tự chèn. (3) `list(kept.items())[:top_k]` lấy `top_k` phần tử đầu. (4) `enumerate(..., start=1)` đánh số rank từ 1.
- **Tại sao:** kết quả retrieval phải **xác định** (deterministic): cùng đầu vào → cùng thứ tự, kể cả khi hai chunk bằng điểm. [REPO src/knowledge_assistant/application/retrieval/retrieve.py:1-9]
- **Pitfalls:** `[GENERAL]` `[]`/`{}` mặc định trong tham số hàm là bẫy kinh điển (dùng chung giữa các lần gọi); repo dùng `None` hoặc `field(default_factory=...)` thay thế.

### 1.6 Comprehension: `[x for x in xs if ...]`
- **Ý tưởng:** cú pháp gọn để tạo list/dict/set/generator từ vòng lặp + điều kiện.
- **C# analogy:** LINQ `xs.Where(...).Select(...).ToList()`; `{k: v for ...}` ≈ `ToDictionary`.
- **Trong repo này:** repo có ~907 comprehension. Ví dụ đọc được ngay:
**`src/knowledge_assistant/application/evaluation/stats.py:40-41`**
```python
    b_count = sum(1 for x, y in zip(a, b) if bool(x) and not bool(y))
    c_count = sum(1 for x, y in zip(a, b) if not bool(x) and bool(y))
```
  và trong `answer_question.py` (kiểm tra key sai): [REPO src/knowledge_assistant/application/generation/answer_question.py:51]. Cú pháp `sum(1 for x, y in zip(a, b) if bool(x) and not bool(y))` = "đếm số cặp (x,y) thoả điều kiện" — generator expression, không tạo list trung gian.
- **Tại sao:** thay vòng `for` + `append` bằng một biểu thức đọc như câu.
- **Pitfalls:** `[GENERAL]` comprehension lồng nhau nhiều tầng khó đọc; nếu quá 2 điều kiện, repo thường tách thành vòng `for` (ví dụ `_code_spans` trong [REPO src/knowledge_assistant/application/citation/citations.py:26-50]).

### 1.7 Exception: `try/except`, `raise ... from`
- **Ý tưởng:** `try: ... except (A, B) as e: ...`; `raise NewError(...) from e` gắn nguyên nhân gốc (`__cause__`).
- **C# analogy:** `try/catch (A or B e)`; `throw new NewError(msg, innerException: e)`.
- **Trong repo này:**
**`src/knowledge_assistant/application/generation/answer_question.py:36-56`**
```python
def parse_answer_json(text: str) -> dict:
    """The LLM's JSON answer, type-checked against ANSWER_SCHEMA. Raises GenerationError with the raw text."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as error:
        raise GenerationError(f"LLM output is not valid JSON: {error}", raw_text=text) from error
    if not isinstance(data, dict):
        raise GenerationError("LLM output is not a JSON object", raw_text=text)
    checks = {
        "insufficient": lambda v: isinstance(v, bool),
        "answer": lambda v: isinstance(v, str),
        "cited_passages": lambda v: isinstance(v, list)
        and all(isinstance(n, int) and not isinstance(n, bool) for n in v),
        "missing_information": lambda v: isinstance(v, str),
    }
    wrong = [key for key, check in checks.items() if key not in data or not check(data[key])]
    if wrong:
        raise GenerationError(f"LLM JSON has missing or mistyped keys: {wrong}", raw_text=text)
    if not data["insufficient"] and not data["answer"].strip():
        raise GenerationError("LLM answered insufficient=false with an empty answer", raw_text=text)
    return data
```
  Hàm này biến "text từ LLM" thành dict **đã kiểm tra kiểu**, nếu sai thì ném `GenerationError` kèm `raw_text`. Chú ý `isinstance(n, int) and not isinstance(n, bool)`: trong Python `True` cũng là `int`, nên phải loại `bool` rõ ràng.
- **Tại sao:** LLM có thể trả JSON hỏng; luật dự án: output không dùng được thì **báo lỗi**, tuyệt đối không biến thành "insufficient" (docstring đầu file). [REPO src/knowledge_assistant/application/generation/answer_question.py:1-9]
- **Pitfalls:** `[GENERAL]` `except Exception: pass` nuốt lỗi — repo tránh; nơi bắt `Exception` rộng đều có comment lý do và log (ví dụ hook ở [REPO src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py:196-200]). `[REAL]` ở chính hook đó từng có bug: hook không được bảo vệ, một hook ném lỗi sẽ làm vòng retry kết thúc sớm; verifier bắt được và sửa bằng guard + test đột biến. [REPO AI_WORKLOG.md:829-831]

### 1.8 `pathlib.Path` và `with`
- **Ý tưởng:** `Path` là object đường dẫn; toán tử `/` nối đường dẫn; có `.read_text()`, `.exists()`, `.mkdir()`. `with open(...) as f:` đảm bảo đóng file.
- **C# analogy:** `Path.Combine` + `File.ReadAllText` gộp làm một; `with` ≈ `using`.
- **Trong repo này:** [REPO src/knowledge_assistant/config.py:12-15] (toán tử `/`), [REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:28-30].
- **Tại sao:** tránh nối chuỗi đường dẫn thủ công, chạy được cả Windows lẫn Linux.
- **Pitfalls:** `[GENERAL]` trên Windows nhớ mở file text với `encoding="utf-8"` (repo luôn ghi rõ) kẻo bị mã hoá theo locale.

---

## Level 2 — Intermediate

### 2.1 Class, `__init__`, `self`, và quy ước `_private`
- **Ý tưởng:** `self` là tham số đầu tiên tường minh (≈ `this`). Field khai báo bằng cách gán `self.x = ...` trong `__init__`. Tên bắt đầu `_` = nội bộ (chỉ quy ước).
- **C# analogy:** constructor + field `private readonly`. Không có từ khoá `private`.
- **Trong repo này:**
**`src/knowledge_assistant/application/retrieval/retrieve.py:48-63`**
```python
class Retriever:
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        top_k: int = 5,
        overfetch: int = 10,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        if top_k < 1 or overfetch < 0:
            raise ValueError(f"top_k must be >= 1 and overfetch >= 0, got {top_k}, {overfetch}")
        self._embedder = embedder
        self._store = store
        self.top_k = top_k
        self.overfetch = overfetch
        self._clock = clock
```
  Ba tham số cuối có giá trị mặc định; `clock` nhận **một hàm** (`time.perf_counter`) làm dependency — xem 2.3.
- **Tại sao:** class chỉ nhận thứ nó cần (embedder, store, cấu hình) qua constructor: constructor injection giống C#.
- **Pitfalls:** `[GENERAL]` quên `self.` trước tên field là lỗi thường gặp; bên trong method, `x` và `self.x` là hai thứ khác nhau.

### 2.2 `Protocol` ≈ interface với structural typing
- **Ý tưởng:** `Protocol` mô tả "hình dạng" (method nào phải có). Class **không cần khai báo** kế thừa; chỉ cần có method đúng chữ ký là được coi thoả (duck typing có kiểm tra tĩnh).
- **C# analogy:** `interface ILlm`, nhưng ở C# phải viết `class GeminiLlm : ILlm`. Ở Python, `GeminiLLM` **không** ghi "implements LLM" nhưng vẫn dùng được ở nơi cần `LLM`.
- **Trong repo này:**
**`src/knowledge_assistant/core/interfaces/llm.py:36-37`**
```python
class LLM(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...
```
**`src/knowledge_assistant/core/interfaces/embedding.py:12-18`**
```python
class Embedder(Protocol):
    @property
    def model_id(self) -> str:
        """Model name plus output size; used as the cache and collection key."""
        ...

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]: ...
```
  `...` (Ellipsis) là "thân hàm rỗng" — giống `throw new NotImplementedException()` nhưng chỉ để khai báo. `@property` trong Protocol nghĩa là "phải có thuộc tính `model_id`".
- **Tại sao:** core định nghĩa "cổng" (port); infrastructure cắm adapter vào mà core không biết Gemini/Chroma (file 03).
- **Pitfalls:** `[GENERAL]` vì không có `implements`, sai chữ ký chỉ bị phát hiện bởi mypy hoặc **lúc chạy**. Repo bù bằng test: ví dụ "mọi member của protocol có trên `CachingEmbedder` với cùng chữ ký". [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:123]

### 2.3 Truyền hàm làm dependency: `clock`, `sleep`, `jitter`
- **Ý tưởng:** hàm là object hạng nhất, truyền như tham số. Giá trị mặc định là hàm thật (`time.sleep`), test truyền hàm giả.
- **C# analogy:** `Func<double>`/`Action<double>` hoặc `TimeProvider`/`ISystemClock` được inject.
- **Trong repo này:**
**`src/knowledge_assistant/infrastructure/embeddings/throttle.py:24-38`**
```python
    def __init__(
        self,
        requests_per_window: int,
        tokens_per_window: int,
        window_s: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._max_requests = requests_per_window
        self._max_tokens = tokens_per_window
        self._window_s = window_s
        self._clock = clock
        self._sleep = sleep
        self._sent: deque[tuple[float, int, int]] = deque()  # (time, requests, estimated tokens)
        self.total_wait_s = 0.0
```
  Kiểu `Callable[[float], None]` nghĩa "hàm nhận 1 float, không trả gì". `deque` là hàng đợi hai đầu (≈ `LinkedList<T>`/`Queue<T>` có `popleft`).
- **Tại sao:** throttle phải chờ thật hàng chục giây; test thay `sleep` bằng hàm ghi lại số giây và `clock` bằng đồng hồ giả để chạy tức thì và xác định. Ví dụ: throttle 3 request/60s, gọi 4 lần với đồng hồ giả → 3 lần đầu chờ 0s, lần 4 chờ 60s (đã chạy thử offline).
- **Pitfalls:** `[GENERAL]` đặt default `clock=time.monotonic` (tham chiếu hàm, **không** có `()`); viết `time.monotonic()` sẽ gọi ngay lúc định nghĩa hàm và cố định giá trị — lỗi kinh điển.

### 2.4 Keyword-only argument (`*`) và `**kwargs`
- **Ý tưởng:** sau dấu `*` trong danh sách tham số, mọi tham số **bắt buộc** gọi theo tên. `**details` gom các tham số theo tên còn lại thành dict.
- **C# analogy:** named arguments bắt buộc (C# không ép được; Python ép được). `**details` ≈ chuyển tiếp `params`/object initializer.
- **Trong repo này:**
**`src/knowledge_assistant/composition.py:58-65`**
```python
def build_answer_service(
    arm: str,
    llm: LLM,
    embedder: Embedder,
    *,
    store: VectorStore | None = None,
    gate_off: bool = False,
) -> AnswerQuestion:
```
**`src/knowledge_assistant/core/exceptions/__init__.py:68-75`**
```python
class LLMQuotaError(LLMError):
    """HTTP 429: the per-minute rate limit persisted through every attempt, or the daily quota is used up."""

    kind = "quota"

    def __init__(self, message: str, *, daily: bool = False, **details) -> None:
        super().__init__(message, **details)
        self.daily = daily  # True: retrying is pointless until the daily reset
```
  Ở `LLMQuotaError`, `**details` nhận `model=..., retry_count=...` rồi `super().__init__(message, **details)` chuyển nguyên xuống lớp cha.
- **Tại sao:** `build_answer_service(arm, llm, embedder, gate_off=True)` đọc rõ nghĩa hơn `(..., True)`; boolean "trần" dễ gọi nhầm.
- **Pitfalls:** `[GENERAL]` sai tên tham số theo tên chỉ lộ ra khi chạy (TypeError).

### 2.5 Context manager: `with`, `__enter__/__exit__`, `@contextmanager`
- **Ý tưởng:** đối tượng dùng được trong `with` nếu có `__enter__` và `__exit__`; cách ngắn hơn là hàm generator có `yield` + decorator `@contextlib.contextmanager` (code trước `yield` = setup, sau `yield` = cleanup).
- **C# analogy:** `IDisposable` + `using`. `@contextmanager` ≈ viết một `using` helper bằng iterator.
- **Trong repo này:**
**`src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:92-96`**
```python
    def __enter__(self) -> "CachingEmbedder":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
```
**`scripts/ask.py:84-89`**
```python
@contextlib.contextmanager
def open_service(arm: str, gate_off: bool):
    """(AnswerQuestion, GeminiLLM) for one arm; the query embedder is closed on exit."""
    llm = GeminiLLM()
    with open_embedder() as embedder:
        yield build_answer_service(arm, llm, embedder, gate_off=gate_off), llm
```
  `yield build_answer_service(...), llm` trả **một tuple** cho biến sau `as`. Khi khối `with` kết thúc (kể cả lỗi), phần thoát của `with open_embedder()` chạy → đóng SQLite.
- **Tại sao:** đảm bảo đóng kết nối SQLite dù có exception.
- **Pitfalls:** `[GENERAL]` `with self._db:` ở [REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:160] là một *transaction* (commit/rollback), **không** đóng connection — cùng cú pháp `with`, ý nghĩa khác nhau tuỳ object.

### 2.6 `Enum` trộn `str`, và dict-lookup thay cho `switch`
- **Ý tưởng:** `class EmbeddingTask(str, Enum)` là enum mà giá trị so sánh được với chuỗi. Dict tra cứu thay cho chuỗi `if/elif`/`switch`.
- **C# analogy:** `enum` + `switch` expression; ở đây bảng dict `TASK_TYPES = {DOCUMENT: "RETRIEVAL_DOCUMENT", ...}` ≈ `Dictionary<EmbeddingTask,string>`.
- **Trong repo này:**
**`src/knowledge_assistant/core/interfaces/embedding.py:5-9`**
```python
class EmbeddingTask(str, Enum):
    """What a text is embedded for. Provider task-type strings live in infrastructure only."""

    DOCUMENT = "document"
    QUERY = "query"
```
  Bảng ánh xạ chuỗi nhà cung cấp chỉ nằm trong infrastructure: [REPO src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:28-31].
- **Tại sao:** core không được biết chuỗi `RETRIEVAL_QUERY` của Google (docstring: "Provider task-type strings live in infrastructure only").
- **Pitfalls:** `[GENERAL]` so sánh enum bằng `is`/`==` đều được; không dùng `int` ma thuật.

### 2.7 Hệ thống exception có phân cấp và thuộc tính lớp (`kind`)
- **Ý tưởng:** exception là class; lớp con ghi đè **thuộc tính lớp** (`kind = "quota"`), không cần `if` để phân loại.
- **C# analogy:** hierarchy `Exception` tuỳ chỉnh; thuộc tính lớp ≈ `virtual string Kind => "other"` override ở lớp con.
- **Trong repo này:**
**`src/knowledge_assistant/core/exceptions/__init__.py:41-50`**
```python
class LLMError(KnowledgeAssistantError):
    """The LLM provider could not answer, after retries and the fallback (ADR-0004 amendment 2026-09-26, RAG-003).

    Provider and transport exceptions never leave the infrastructure layer: they are wrapped into one of the three
    subtypes below, whose `kind` is the GUI's `AskQuestionError.kind` (quota | unavailable | other), 1:1. This base
    class is `other`. `model` is the answer model, `retry_count` its retries, `provider_body` the answer model's error
    body with any key redacted (for logs). The message is safe to show and log: it never contains the API key.
    """

    kind = "other"
```
- **Tại sao:** GUI cần "kind" (quota/unavailable/other); `LLMError.kind` được thiết kế ánh xạ 1:1 sang GUI (xem file 03, 09).
- **Pitfalls:** `[GENERAL]` chỉ bắt `except Exception` ở ranh giới hệ thống (ví dụ GUI adapter [REPO src/knowledge_assistant/presentation/desktop/viewmodels/core_ask_question.py:66-72]).

### 2.8 `lambda`, "dict of checks", và `dict.fromkeys` làm ordered set
- **Ý tưởng:** `lambda v: isinstance(v, bool)` = hàm một dòng vô danh. Một dict `{tên: hàm kiểm}` cho phép lặp qua các quy tắc. `list(dict.fromkeys(xs))` loại trùng **giữ thứ tự** xuất hiện đầu tiên.
- **C# analogy:** `x => x is bool`; `Dictionary<string, Func<object,bool>>`; `Distinct()` (giữ thứ tự).
- **Trong repo này:**
**`src/knowledge_assistant/application/generation/answer_question.py:44-50`**
```python
    checks = {
        "insufficient": lambda v: isinstance(v, bool),
        "answer": lambda v: isinstance(v, str),
        "cited_passages": lambda v: isinstance(v, list)
        and all(isinstance(n, int) and not isinstance(n, bool) for n in v),
        "missing_information": lambda v: isinstance(v, str),
    }
```
**`src/knowledge_assistant/application/citation/citations.py:88-90`**
```python
def extract_markers(answer: str) -> list[int]:
    """Marker numbers (outside code, n >= 1) in order of first appearance, without repeats."""
    return list(dict.fromkeys(int(m.group(1)) for m in _marker_matches(answer, _MARKER)))
```
- **Tại sao:** `extract_markers` trả các số `[n]` theo thứ tự xuất hiện đầu tiên, không lặp: đầu ra ổn định.
- **Pitfalls:** `[GENERAL]` `set` **không** giữ thứ tự nên không dùng để khử trùng khi thứ tự quan trọng.

### 2.9 Ba tiện ích chuẩn hay gặp: `defaultdict`, `bisect`, `replace`/`asdict`
- **`collections.defaultdict(list)`:** dict tự tạo giá trị mặc định khi khoá chưa có, nên `d[k].append(x)` chạy được ngay không cần kiểm `if k not in d`. Trong repo, chỉ mục section gom nhiều span theo khoá `(source_id, heading_path)`:
**`src/knowledge_assistant/application/evaluation/metrics/spans.py:28-36`**
```python
def section_index(normalized_records: list[dict]) -> dict[tuple[str, str], list[tuple[int, int, int]]]:
    """{(source_id, heading_path): [(variant, char_start, char_end), ...]} in document order."""
    index = defaultdict(list)
    for record in normalized_records:
        for section in record["metadata"]["sections"]:
            index[(record["id"], section["heading_path"])].append(
                (section["variant"], section["char_start"], section["char_end"])
            )
    return dict(index)
```
  Cuối hàm `dict(index)` đổi về dict thường để bên ngoài không vô tình tạo khoá mới khi tra cứu. **C# analogy:** `Dictionary<K, List<V>>` cộng với `TryGetValue`/`GetOrAdd`, hoặc `ILookup`.
- **`bisect.bisect_right`:** tìm vị trí chèn trong danh sách **đã sắp xếp** bằng tìm nhị phân (O(log n)). Ở đây dùng để tìm section chứa một vị trí ký tự: lấy danh sách điểm bắt đầu các section rồi `bisect_right(starts, position) - 1` là chỉ số section có điểm bắt đầu ≤ vị trí:
**`src/knowledge_assistant/infrastructure/chunking/chunk_builder.py:44-48`**
```python
def section_path_at(document: ParsedDocument, position: int) -> tuple[str, ...]:
    """Heading path of the H1-H3 section that contains `position` (the nearest heading before it)."""
    starts = [section.char_start for section in document.sections]
    index = bisect_right(starts, position) - 1
    return document.sections[index].heading_path if index >= 0 else ()
```
  **C# analogy:** `Array.BinarySearch`/`List<T>.BinarySearch`. **Pitfall `[GENERAL]`:** danh sách **bắt buộc đã sắp xếp**; nếu không, kết quả sai mà không báo lỗi.
- **`dataclasses.replace` và `asdict`:** với dataclass `frozen=True` (bất biến, mục 1.3), muốn "sửa một trường" thì tạo **bản sao** có trường khác: `replace(chunk, duplicates=())` ([REPO src/knowledge_assistant/application/evaluation/metrics/retrieval.py:226]) — giống `with` expression của `record` trong C# (`chunk with { Duplicates = ... }`). `asdict(self)` biến dataclass thành dict để ghi JSON (ví dụ `RunConfig.to_dict()` ở [REPO src/knowledge_assistant/application/evaluation/run_evaluation.py:89-90]).
- **Tại sao đáng biết:** ba hàm này xuất hiện ở nhiều file; nhận ra chúng giúp bạn đọc nhanh mà không phải dừng lại tra.

---

## Level 3 — Advanced

### 3.1 Regex như một mini-parser (biên dịch một lần ở cấp module)
- **Ý tưởng:** `re.compile(...)` tạo object pattern dùng lại; ghép nhiều pattern nhỏ có tên. `(?<!...)` là *lookbehind*, `(?=...)` là *lookahead* (không "ăn" ký tự).
- **C# analogy:** `Regex` với `RegexOptions.Compiled`; cú pháp lookbehind giống nhau.
- **Trong repo này:**
**`src/knowledge_assistant/application/citation/citations.py:16-23`**
```python
_MARKER = re.compile(r"\[(\d+)\]")
_MARKER_WITH_SPACE = re.compile(r"[ \t]*\[(\d+)\]")
# A sentence ends at . ! or ? (plus any markers right after it) before whitespace or the end, or at a line break.
_SENTENCE_END = re.compile(r"[.!?]+(?:[ \t]*\[\d+\])*(?=\s|$)|\n+")
_WORD = re.compile(r"\w+")
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_INLINE_CODE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)
_NOT_A_MARKER = "\x00"  # replaces the "[" of a non-marker `[n]`, inside `count_uncited_sentences` only
```
  `_INLINE_CODE` khớp "cụm backtick đóng bởi cụm backtick cùng độ dài" (markdown inline code), dùng lookbehind/lookahead để không nhầm với cụm dài hơn.
- **Tại sao:** marker trích dẫn `[n]` chỉ là marker khi **nằm ngoài code**. `[REAL]` bản đầu của RAG-002 khớp `[n]` cả trong code (ví dụ chỉ mục C# `args[0]`); verifier bắt lỗi F1, sửa ở commit `ba5aa59` và kiểm bằng mutation test. [REPO AI_WORKLOG.md:823-825]. Đã chạy thử offline: ``extract_markers("a [1] b `x[2]` [3] [1] [0]")`` (thêm một khối code rào bằng ba dấu backtick chứa `q[4]`) trả về `[1, 3]`.
- **Pitfalls:** `[GENERAL]` regex greedy vs non-greedy (`.+?`) và cờ `re.DOTALL`; thử regex quan trọng bằng test nhiều ca biên.

### 3.2 Dữ liệu nhị phân: `struct`, `bytes`
- **Ý tưởng:** `struct.pack("<768f", *vector)` biến 768 số float thành bytes (little-endian float32); `struct.unpack` làm ngược lại. `*vector` "bung" list thành từng tham số.
- **C# analogy:** `BitConverter`/`MemoryMarshal.Cast<float,byte>`; `*vector` ≈ `params`/spread.
- **Trong repo này:**
**`src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:36-41`**
```python
def _to_blob(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _from_blob(blob: bytes, dim: int) -> list[float]:
    return list(struct.unpack(f"<{dim}f", blob))
```
- **Tại sao:** lưu vector vào cột BLOB của SQLite gọn (4 byte/số) thay vì JSON. Chi tiết trong file 04/06.
- **Pitfalls:** `[GENERAL]` float32 làm tròn — repo cố ý trả về giá trị **đã qua float32 ngay lần miss đầu tiên** để kết quả không phụ thuộc cache đã có hay chưa. [REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:159]

### 3.3 Số học chính xác với `fractions.Fraction` và `math.comb`
- **Ý tưởng:** `Fraction(5, 16)` giữ phân số đúng, không sai số float; `math.comb(n, k)` = C(n,k).
- **C# analogy:** `System.Numerics.BigInteger` + tự viết phân số (C# không có sẵn `Fraction`); `decimal` gần đúng hơn `double` nhưng vẫn không chính xác.
- **Trong repo này:**
**`src/knowledge_assistant/application/evaluation/stats.py:34-46`**
```python
def mcnemar_exact(a: list[int | bool], b: list[int | bool]) -> McNemarResult:
    """Exact McNemar: under H0 the b + c discordant pairs split Binomial(b + c, 1/2).

    p = min(1, 2 * sum_{i <= min(b, c)} C(n, i) / 2^n), computed with exact fractions; no discordant pairs -> p = 1.
    """
    _paired(a, b)
    b_count = sum(1 for x, y in zip(a, b) if bool(x) and not bool(y))
    c_count = sum(1 for x, y in zip(a, b) if not bool(x) and bool(y))
    n = b_count + c_count
    if n == 0:
        return McNemarResult(b_count, c_count, 1.0)
    tail = Fraction(sum(math.comb(n, i) for i in range(min(b_count, c_count) + 1)), 2 ** n)
    return McNemarResult(b_count, c_count, float(min(Fraction(1), 2 * tail)))
```
  Đọc: đếm cặp "khác kết quả" (b: A đúng B sai; c: A sai B đúng), `n = b + c`; p-value hai phía = `min(1, 2 * P(X ≤ min(b,c)))` với X ~ Binomial(n, 1/2). Ví dụ đã chạy thử: A=[1,1,1,0,0,1,1,1], B=[0,0,1,1,0,1,1,0] → b=3, c=1, p=0.625 (vì 2·(1+4)/16 = 0.625). Đây chỉ là ví dụ để luyện đọc cú pháp; **home** của McNemar và các kiểm định là file 12 (thống kê).
- **Tại sao:** thống kê của thí nghiệm cần kết quả tái lập chính xác, không lệch do float.
- **Pitfalls:** `[GENERAL]` Python `int` không tràn (khác C#), nên `2 ** n` an toàn.

### 3.4 Kiểm tra bất biến trong `__post_init__`
- **Ý tưởng:** `dataclass` gọi `__post_init__` sau `__init__` để kiểm tra dữ liệu hợp lệ.
- **C# analogy:** kiểm tra trong constructor của `record` (`init` accessor/guard clause).
- **Trong repo này:**
**`src/knowledge_assistant/infrastructure/chunking/header_aware.py:29-39`**
```python
@dataclass(frozen=True)
class HeaderAwareConfig:
    chunker_config: str
    max_chars: int
    min_chars: int
    overlap_chars: int
    drop_heading_only: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.overlap_chars < self.max_chars or not 0 <= self.min_chars <= self.max_chars:
            raise ValueError("need 0 <= overlap_chars < max_chars and 0 <= min_chars <= max_chars")
```
- **Tại sao:** cấu hình sai (overlap ≥ max) sẽ làm chunker chạy vô hạn hoặc vô nghĩa; fail sớm, to tiếng.
- **Pitfalls:** `[GENERAL]` `frozen=True` + `__post_init__` chỉ được đọc field, không gán (gán sẽ lỗi).

### 3.5 `getattr` với default: đối tượng của SDK bên ngoài
- **Ý tưởng:** `getattr(obj, "name", None)` đọc thuộc tính nếu có, không thì `None`, không ném lỗi.
- **C# analogy:** `dynamic`/reflection + `?.`; hoặc `TryGetValue`.
- **Trong repo này:**
**`src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py:57-60`**
```python
def _finish_reason(response: Any) -> str | None:
    candidates = getattr(response, "candidates", None) or []
    reason = getattr(candidates[0], "finish_reason", None) if candidates else None
    return getattr(reason, "name", None) or (str(reason) if reason is not None else None)
```
- **Tại sao:** phản hồi của SDK có thể thiếu `candidates`/`usage_metadata`; code cần "None khi provider không báo", **không** điền số 0 giả (luật: đừng bịa số). [REPO src/knowledge_assistant/core/interfaces/llm.py:20-22]
- **Pitfalls:** `[GENERAL]` `getattr` che lỗi gõ sai tên thuộc tính; chỉ dùng ở ranh giới với thư viện ngoài, đúng như repo.

### 3.6 `from __future__ import annotations` và chú thích kiểu dạng chuỗi
- **Ý tưởng:** cho phép dùng tên class **chưa định nghĩa** trong type hint (`"QtExecutor"` hoặc dòng import trên đầu); hint không được đánh giá lúc chạy.
- **C# analogy:** C# không cần vì compiler nhìn toàn assembly; Python chạy từ trên xuống nên cần.
- **Trong repo này:**
**`src/knowledge_assistant/presentation/desktop/workers.py:1-8`**
```python
"""Qt thread-pool executor: runs the port call off the GUI thread, delivers callbacks on the GUI thread."""
from __future__ import annotations

import itertools
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

```
  Dòng `_owner: "QtExecutor"` ở [REPO src/knowledge_assistant/presentation/desktop/workers.py:11] tham chiếu class khai báo **bên dưới**.
- **Tại sao:** `_Job` cần biết `QtExecutor` nhưng `QtExecutor` dùng `_Job`; tham chiếu chuỗi phá vòng.
- **Pitfalls:** `[GENERAL]` khi runtime cần thật sự tra cứu hint (một số thư viện validation) thì cách này có thể khác hành vi.

---

## Exercises (tất cả offline; đáp án trong `<details>`)

**B1 (Basic).** Đọc [REPO src/knowledge_assistant/config.py:12-15]. `resolve_project_path("data/chroma")` và `resolve_project_path("C:/x/y")` trả về gì (mô tả)?
<details><summary>Đáp án</summary>
Đường dẫn tương đối → `PROJECT_ROOT / "data/chroma"` (nối từ gốc repo). Đường dẫn tuyệt đối → giữ nguyên `Path("C:/x/y")`. Dòng quyết định: `return path if path.is_absolute() else PROJECT_ROOT / path`.
</details>

**B2 (Basic).** `os.getenv("GEMINI_API_KEY") or None` — nếu biến đặt thành chuỗi rỗng thì kết quả?
<details><summary>Đáp án</summary>
`None`, vì `""` là falsy nên `"" or None` cho `None`. Đây là ý đồ: chuỗi rỗng coi như chưa cấu hình ([REPO src/knowledge_assistant/config.py:35]).
</details>

**B3 (Basic).** Vì sao `parse_answer_json` phải viết `not isinstance(n, bool)` khi kiểm `cited_passages`?
<details><summary>Đáp án</summary>
`bool` là lớp con của `int` trong Python: `isinstance(True, int)` là `True`. Nếu không loại `bool`, `[true]` từ LLM sẽ bị coi là danh sách số nguyên hợp lệ ([REPO src/knowledge_assistant/application/generation/answer_question.py:47-48]).
</details>

**I1 (Intermediate).** Không chạy code: `l2_normalize([3.0, 4.0])` trả về gì? Xem [REPO src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:37-41]. Sau đó tự chạy để kiểm.
<details><summary>Đáp án</summary>
Norm = √(3²+4²) = 5 → `[0.6, 0.8]` (đã chạy thử). Độ dài vector mới = 1, nên cosine giữa hai vector chuẩn hoá bằng tích vô hướng.
</details>

**I2 (Intermediate).** Tính bằng tay `backoff_wait_s(attempt, None, 0.5)` cho attempt = 1..4, rồi `backoff_wait_s(2, 10.0, 0.5)` và `backoff_wait_s(8, None, 0.0)`. Xem [REPO src/knowledge_assistant/infrastructure/gemini_retry.py:104-108].
<details><summary>Đáp án</summary>
Công thức: `min(max(1.0·2^(attempt−1) + jitter, retry_after or 0), 120)`. attempt 1..4 với jitter 0.5 → `1.5, 2.5, 4.5, 8.5`. Với retry_after=10 và attempt 2: max(2.5, 10) = `10.0`. Với attempt 8: 2^7 = 128 → bị chặn ở `120.0`. (Đã chạy thử offline.)
</details>

**I3 (Intermediate).** `collection_name("header-1600", "gemini-embedding-001@768")` cho tên gì và vì sao ký tự `@` đổi?
<details><summary>Đáp án</summary>
`kb_header-1600_gemini-embedding-001-768`. `NAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")` thay mọi ký tự ngoài bộ cho phép bằng `-` vì Chroma cấm `@` trong tên collection ([REPO src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:23-29]).
</details>

**A1 (Advanced).** Trong `SlidingWindowThrottle.acquire`, đâu là điều kiện thoát vòng `while True`, và `wait` được tính thế nào khi chưa đủ chỗ? Với throttle `(3 request, 1000 token, 60s)` và đồng hồ giả bắt đầu ở 0, gọi `acquire(10)` bốn lần liên tiếp thì mỗi lần chờ bao lâu?
<details><summary>Đáp án</summary>
Thoát khi `used_requests + requests <= max_requests` **và** `used_tokens + tokens <= max_tokens` (thì ghi lại và `return waited`). Nếu chưa đủ: `wait = self._sent[0][0] + self._window_s - now` (chờ đến khi lời gọi cũ nhất rời khỏi cửa sổ 60s), rồi lặp lại. Bốn lần: `[0.0, 0.0, 0.0, 60.0]`, `sleep` được gọi đúng một lần với 60.0 (đã chạy thử). [REPO src/knowledge_assistant/infrastructure/embeddings/throttle.py:40-60]
</details>

**A2 (Advanced).** ``extract_markers("a [1] b `x[2]` [3] [1] [0]")`` trả `[1, 3]`. Giải thích từng số bị loại/giữ.
<details><summary>Đáp án</summary>
`[1]` giữ (lần đầu). `[2]` nằm trong inline code → không phải marker. `[3]` giữ. `[1]` thứ hai bị `dict.fromkeys` loại (trùng). `[0]` không phải marker vì `int(number) >= 1` sai ([REPO src/knowledge_assistant/application/citation/citations.py:53-55]).
</details>

## Self-check questions
1. `Protocol` khác `interface` của C# ở điểm nào quan trọng nhất khi triển khai?
2. Vì sao repo dùng `tuple` thay `list` trong dataclass `frozen`?
3. `with` dùng cho `using`-style cleanup và cho transaction — hai ví dụ trong repo là gì?
4. Vì sao hàm nhận `clock`/`sleep`/`jitter` mà không gọi `time.sleep` trực tiếp?
5. Giải thích `list(dict.fromkeys(xs))`.

## Interview Q&A
1. **"Python type hints có được ép lúc chạy không?"** — Không. Trong repo, nơi cần bảo đảm kiểu (output của LLM), code tự kiểm tra bằng `isinstance` ([REPO src/knowledge_assistant/application/generation/answer_question.py:36-56]).
2. **"Structural typing là gì, dùng ở đâu?"** — Class thoả `Protocol` nếu có đúng method; repo dùng để core định nghĩa cổng (`LLM`, `Embedder`, `VectorStore`) mà adapter không cần kế thừa ([REPO src/knowledge_assistant/core/interfaces/llm.py:36-37]).
3. **"Vì sao inject clock/sleep?"** — Để test code phụ thuộc thời gian chạy tức thì và xác định ([REPO src/knowledge_assistant/infrastructure/embeddings/throttle.py:24-31]).
4. **"Khi nào bắt `except Exception`?"** — Chỉ ở ranh giới, có lý do và log; ví dụ hook quan sát không được làm đổi hành vi retry ([REPO src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py:196-200]).
5. **"Dataclass frozen giải quyết gì?"** — Dữ liệu chảy giữa layer bất biến, có equality theo giá trị, ≈ `record` C#.

## Further reading
- Tài liệu Python chính thức: *The Python Tutorial*, *dataclasses*, *typing.Protocol*, *contextlib*, *pathlib*, *re* (docs.python.org).
- PEP 544 (Protocols: structural subtyping), PEP 557 (Data Classes). `[GENERAL]`
- Tiếp theo: [01b — Hướng dẫn đọc code Python](01b-python-code-reading-guide.md), rồi [03 — Kiến trúc](03-architecture-and-gui.md).
