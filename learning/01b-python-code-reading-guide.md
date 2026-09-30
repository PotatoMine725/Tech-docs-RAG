# 01b · Hướng dẫn đọc hiểu code Python (bảng giải mã + template)
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [01](01-python-for-csharp-devs.md) (đọc song song được) · Study time: ~4–5h · Mục tiêu: **đọc và hiểu** code Python, không cần tự viết tay
> Quy ước: khối code có dòng tiêu đề `path:dòng` là **trích nguyên văn từ repo** `[REPO]`. Khối "Template" là mẫu chung `[GENERAL]` do tôi viết để minh hoạ cú pháp, **không** phải code của repo.

## Vì sao file này quan trọng trong dự án
Dự án do AI agent viết; bạn là người review/bảo vệ nó. Bạn không cần gõ Python thành thạo, nhưng phải **đọc một hàm lạ và nói được nó làm gì, vì sao, và chỗ nào có thể sai**. File này cho bạn: (1) quy trình đọc, (2) bảng giải mã ký hiệu, (3) ~30 template cú pháp kèm ví dụ thật từ repo, (4) bài tập "chạy bằng đầu" có đáp án đã kiểm chứng.

---

## Level 1 — Basic: quy trình đọc và ký hiệu

### 1.1 Quy trình đọc một file Python trong 6 bước
1. **Docstring đầu file** (chuỗi `"""..."""` trên cùng): repo này viết docstring rất kỹ, thường nêu luật và tên task/ADR. Đọc trước — nó là "spec" của file.
2. **`import`**: cho biết file phụ thuộc gì. Trong repo, import cho biết layer (core/application/infrastructure): file `core/` không được import `chromadb`/`google` (xem file 03).
3. **Hằng số cấp module** (tên VIẾT_HOA, regex `_TÊN = re.compile(...)`): các "con số ma thuật" đã được đặt tên.
4. **Kiểu dữ liệu** (`@dataclass`, `Protocol`): "danh từ" của file.
5. **Hàm/class công khai** (không bắt đầu bằng `_`): "động từ" — API mà file khác dùng. Hàm `_private` đọc sau.
6. **Chạy bằng đầu một ví dụ nhỏ** (mục 3): chọn 1 đầu vào cụ thể, lần theo từng dòng.

### 1.2 Cấu trúc một hàm: đọc từ trên xuống
Ví dụ thật, hàm nhỏ và đủ bộ phận:
**`src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:37-41`**
```python
def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        raise EmbeddingError("provider returned a zero vector")
    return [v / norm for v in vector]
```
Đọc như sau: **chữ ký** `def l2_normalize(vector: list[float]) -> list[float]` (nhận list số thực, trả list số thực) → **tính** `norm` (căn tổng bình phương; generator expression trong `sum(...)`) → **guard clause** (`if norm == 0.0: raise ...` — chặn trường hợp lỗi sớm) → **trả** list chia cho norm (list comprehension). Mẫu "tính → chặn lỗi → trả" lặp lại khắp repo.

### 1.3 Bảng giải mã ký hiệu (bookmark bảng này)
| Ký hiệu | Đọc là | Tương đương C# | Ví dụ trong repo |
|---|---|---|---|
| `x: T` | "x có kiểu gợi ý T" | `T x` | [REPO src/knowledge_assistant/config.py:12] |
| `-> T` | "trả về kiểu T" | kiểu trả về | [REPO src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:37] |
| `T \| None` | "T hoặc None" | `T?` | [REPO src/knowledge_assistant/core/models/__init__.py:16] |
| `list[str]`, `dict[str, int]` | list/dict có kiểu phần tử | `List<string>`, `Dictionary<string,int>` | [REPO src/knowledge_assistant/core/interfaces/vector_store.py:9] |
| `tuple[str, ...]` | tuple độ dài tuỳ ý toàn str | `IReadOnlyList<string>` | [REPO src/knowledge_assistant/core/models/__init__.py:56] |
| `self` | đối tượng hiện tại | `this` | [REPO src/knowledge_assistant/application/retrieval/retrieve.py:49-56] |
| `_name` | "nội bộ, đừng dùng từ ngoài" | `private` (chỉ quy ước) | [REPO src/knowledge_assistant/infrastructure/chunking/header_aware.py:79] |
| `__name__` (dunder) | thuộc tính/method đặc biệt của Python | (không có) | [REPO scripts/ask.py:236] |
| `@xyz` trên hàm/class | decorator: bọc/điều chỉnh hàm/class | attribute + AOP | [REPO src/knowledge_assistant/config.py:38] |
| `*args`, `**kwargs` | gom tham số vị trí/theo tên | `params`, không có tương đương trực tiếp | [REPO src/knowledge_assistant/core/exceptions/__init__.py:73] |
| `f(*xs)` / `f(**d)` | "bung" list/dict thành tham số | spread | [REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:37] |
| `*` một mình trong tham số | sau đây bắt buộc gọi theo tên | (không có) | [REPO src/knowledge_assistant/composition.py:62] |
| `a[i:j]` | lát cắt [i, j) | `a[i..j]` / `Substring` | [REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:110] |
| `a[-1]` | phần tử cuối (`a[0]` là đầu) | `a[^1]` | [REPO src/knowledge_assistant/infrastructure/chunking/header_aware.py:122] (`piece[0].start`, `piece[-1].end`) |
| `_` | "biến bỏ đi" | discard `_` | [REPO src/knowledge_assistant/infrastructure/embeddings/throttle.py:52] |
| `:=` | gán trong biểu thức (walrus) | `is var x` (gần đúng) | [REPO scripts/evaluation/score_spot_check.py:133] |
| `x if c else y` | biểu thức điều kiện | `c ? x : y` | [REPO scripts/ask.py:163] |
| `not`, `and`, `or` | phủ định/và/hoặc | `!`, `&&`, `\|\|` | [REPO src/knowledge_assistant/application/evaluation/stats.py:40] |
| `a is None` | so sánh **danh tính** với None | `a == null` | [REPO src/knowledge_assistant/presentation/desktop/viewmodels/ask_viewmodel.py:105] |
| `x in xs` | thuộc tập/list/dict | `xs.Contains(x)` | [REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:105] |
| `...` (Ellipsis) | "chưa viết thân" hoặc "độ dài tuỳ ý" | (không có) | [REPO src/knowledge_assistant/core/interfaces/llm.py:37] |
| `"""..."""` | chuỗi nhiều dòng / docstring | `"""` raw string | [REPO src/knowledge_assistant/composition.py:1-5] |
| `r"..."` | chuỗi thô (không xử lý `\`) | `@"..."` | [REPO src/knowledge_assistant/application/citation/citations.py:16] |
| `b"..."` | bytes | `byte[]` | [REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:53] |
| `# noqa: ...` | bảo linter bỏ qua dòng này | `#pragma warning disable` | [REPO scripts/ask.py:68] |
| `if __name__ == "__main__":` | "chỉ chạy khi file được chạy trực tiếp" | `static void Main` | [REPO scripts/ask.py:236] |

### 1.4 Ba "dấu hiệu" nhận biết nhanh
- **Thụt lề = khối lệnh.** Không có `{ }`. Hai dấu `:` ở cuối dòng `if/for/def/class/with/try` mở khối.
- **Không có `new`, không có `;`.** `Document(...)` là gọi constructor.
- **Mọi thứ là object.** Hàm, class, module đều truyền được (xem `clock=time.perf_counter` ở [REPO src/knowledge_assistant/application/retrieval/retrieve.py:55]).

---

## Level 2 — Intermediate: catalog template

Mỗi mục: **Template** `[GENERAL]` → **Đọc là** → **C#** → **Ví dụ repo**.

### T1 · Hàm có giá trị mặc định + kiểu
Template:
```python
def greet(name: str, times: int = 1, *, loud: bool = False) -> str:
    text = f"hi {name}"
    return text.upper() if loud else text
```
Đọc là: `times` mặc định 1; sau `*` thì `loud` **bắt buộc** gọi theo tên (`greet("a", loud=True)`); dòng cuối là biểu thức điều kiện.
C#: `string Greet(string name, int times = 1, bool loud = false)`.
Ví dụ repo: [REPO src/knowledge_assistant/composition.py:58-65].

### T2 · Guard clause (chặn sớm)
Template:
```python
def area(w, h):
    if w <= 0 or h <= 0:
        raise ValueError("size must be positive")
    return w * h
```
Đọc là: điều kiện sai → ném lỗi ngay, phần còn lại là "đường chính".
Ví dụ repo:
**`src/knowledge_assistant/application/retrieval/retrieve.py:57-58`**
```python
        if top_k < 1 or overfetch < 0:
            raise ValueError(f"top_k must be >= 1 and overfetch >= 0, got {top_k}, {overfetch}")
```
Chú ý so sánh chuỗi (chained comparison) ở [REPO src/knowledge_assistant/infrastructure/chunking/header_aware.py:38]: `0 <= self.overlap_chars < self.max_chars` nghĩa là `0 <= a && a < b` (Python cho viết dây).

### T3 · Vòng lặp `for`: `enumerate`, `zip`, unpack
Template:
```python
for i, (name, score) in enumerate(zip(names, scores), start=1):
    print(i, name, score)
```
Đọc là: ghép hai list theo cặp, đánh số từ 1, "bung" mỗi cặp thành `name`, `score`.
C#: `foreach (var (name, score, i) in names.Zip(scores).Select(...))`.
Ví dụ repo:
**`src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:154-159`**
```python
        stored: dict[str, list[float]] = {}
        rows = []
        for (key, _), vector in zip(batch, vectors):
            blob = _to_blob(vector)
            rows.append((key, self.model_id, task.value, len(vector), blob, now))
            stored[key] = _from_blob(blob, len(vector))  # same float32 values as a later cache hit
```
`for (key, _), vector in zip(batch, vectors)` = mỗi phần tử của `batch` là cặp `(key, text)`; ta chỉ cần `key` và bỏ `text` bằng `_`.

### T4 · Unpack với `*` ("phần còn lại")
Template:
```python
first, *rest = [1, 2, 3]        # first=1, rest=[2, 3]
*head, last = b"a\nb\nc".split(b"\n")
```
Ví dụ repo (đọc: "mọi phần trừ phần cuối là dòng hoàn chỉnh, phần sau newline cuối là 'đuôi rách'"):
**`src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:49-60`**
```python
    def _read(self, name: str) -> list[dict]:
        path = self._dir / name
        if not path.exists():
            return []
        *complete, _torn_tail = path.read_bytes().split(b"\n")  # the piece after the last newline is not a record
        records = []
        for number, line in enumerate(complete, start=1):
            try:
                records.append(json.loads(line.decode("utf-8")))
            except ValueError as error:  # JSONDecodeError and UnicodeDecodeError
                raise EvaluationError(f"{path} {name} line {number} is not valid JSON: {error}") from error
        return records
```
Đã chạy thử: `*complete, tail = b"a\nb\nc".split(b"\n")` → `complete=[b'a', b'b']`, `tail=b'c'`.

### T5 · Comprehension (list/dict/set/generator)
Template:
```python
squares = [x * x for x in xs if x > 0]        # list
by_id   = {c.id: c for c in chunks}           # dict
total   = sum(len(t) for t in texts)          # generator (no intermediate list)
```
C#: `xs.Where(x => x > 0).Select(x => x * x).ToList()`; `ToDictionary`; `texts.Sum(t => t.Length)`.
Ví dụ repo: [REPO src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:41] (`[v / norm for v in vector]`), [REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:151] (`sum(estimate_tokens(t) for t in texts)`).

### T6 · Slice và tính chỉ số
Template:
```python
xs[2:5]      # items 2, 3, 4
xs[:3]       # the first 3 items
xs[i : i + n]  # a window of n items starting at i
```
Ví dụ repo (chia list thành lô 100 phần tử; `range(0, N, step)` nhảy bước):
**`src/knowledge_assistant/application/ingestion/index_corpus.py:91-92`**
```python
            for i in range(0, len(todo), self._upsert_batch):
                self._store.upsert(todo[i : i + self._upsert_batch], vectors[i : i + self._upsert_batch])
```

### T7 · f-string và định dạng
Template:
```python
f"{n:04d}"     # 0007  (zero-padded, width 4)
f"{x:.2f}"     # 3.14
f"{name!r}"    # 'name' (repr, with quotes)
f"{p:.0%}"     # 50%
```
Ví dụ repo: [REPO src/knowledge_assistant/infrastructure/chunking/chunk_builder.py:95] (`{len(chunks):04d}` tạo `chunk_id` kiểu `01:header-1600:0000`), [REPO scripts/ask.py:173-174] (`{shown:.4f}`). Đã chạy thử: `f"{7:04d}|{3.14159:.2f}|{'x'!r}|{0.5:.0%}"` → `0007|3.14|'x'|50%`.

### T8 · `try / except / finally` và `with`
Template:
```python
try:
    value = int(text)
except ValueError as error:
    raise ConfigError("bad number") from error
else:
    print("ok")
finally:
    cleanup()
```
Đọc là: `else` chạy khi **không** có lỗi; `finally` luôn chạy. `raise ... from error` giữ nguyên nhân.
Ví dụ repo: [REPO src/knowledge_assistant/composition.py:45-51] (bắt `FileNotFoundError` rồi ném `VectorStoreError` có hướng dẫn "chạy script nào").

### T9 · Decorator
Template:
```python
@retry(times=3)
def fetch(): ...
# means: fetch = retry(times=3)(fetch)
```
Đọc là: decorator nhận hàm, trả hàm mới (bọc thêm hành vi). Repo dùng decorator **có sẵn**: `@dataclass`, `@property`, `@staticmethod`, `@classmethod`, `@contextlib.contextmanager`, `@pytest.fixture`, `@pytest.mark.parametrize`. Bạn chỉ cần biết ý nghĩa từng cái, không cần viết.
Ví dụ repo: [REPO src/knowledge_assistant/config.py:51-54] (`@property`), [REPO src/knowledge_assistant/application/generation/prompt_builder.py:63-65] (`@classmethod` — factory `PromptBuilder.from_dir(...)`, `cls` là chính class ≈ `static` factory method).

### T10 · Generator: `yield`
Template:
```python
def numbers():
    yield 1
    yield 2      # the function pauses at each yield
```
C#: `IEnumerable<int>` + `yield return`. Trong repo, `yield` chủ yếu xuất hiện trong `@contextlib.contextmanager` (code trước `yield` = setup, sau = cleanup):
**`scripts/ask.py:84-89`**
```python
@contextlib.contextmanager
def open_service(arm: str, gate_off: bool):
    """(AnswerQuestion, GeminiLLM) for one arm; the query embedder is closed on exit."""
    llm = GeminiLLM()
    with open_embedder() as embedder:
        yield build_answer_service(arm, llm, embedder, gate_off=gate_off), llm
```

### T11 · `lambda` và `sorted(key=...)`
Template:
```python
sorted(items, key=lambda it: (-it.score, it.id))
```
Đọc là: sắp theo tuple `(-score, id)`: score giảm dần, hoà thì id tăng dần. C#: `OrderByDescending(x => x.Score).ThenBy(x => x.Id)`.
Ví dụ repo: [REPO src/knowledge_assistant/application/retrieval/retrieve.py:31].

### T12 · `isinstance`, `getattr`, "duck typing"
Template:
```python
if isinstance(err, (LLMError, GenerationError)):    # C#: err is LLMError or GenerationError
    ...
value = getattr(obj, "usage", None)                   # safe attribute read
```
Ví dụ repo: phân loại lỗi thành mã thoát:
**`scripts/ask.py:189-198`**
```python
def classify(error: KnowledgeAssistantError) -> tuple[int, str]:
    if isinstance(error, LLMError):
        return 2, error.kind
    if isinstance(error, GenerationError):
        return 3, "generation"
    if isinstance(error, (ConfigurationError, VectorStoreError)):
        return 4, "setup"
    if isinstance(error, (EmbeddingError, RetrievalError)):
        return 4, "retrieval"
    return 4, "error"
```

### T13 · Argparse (CLI)
Template:
```python
parser = argparse.ArgumentParser()
parser.add_argument("question")                       # positional argument
parser.add_argument("--arm", choices=["A", "B"], default="A")
parser.add_argument("--json", action="store_true")    # boolean flag: present or not
args = parser.parse_args(argv)
```
Đọc là: `args.question`, `args.arm`, `args.json`. `--gate-off` trở thành `args.gate_off` (gạch nối → gạch dưới).
Ví dụ repo:
**`scripts/ask.py:201-210`**
```python
def parse_args(argv: list[str] | None) -> argparse.Namespace:
    epilog = "JSON output (--json):" + __doc__.split("JSON output (--json):", 1)[1]
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0], epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("question")
    parser.add_argument("--arm", choices=ARMS, default="A", help="experiment arm (default A)")
    parser.add_argument("--json", action="store_true", help="print one JSON document instead of text")
    parser.add_argument("--gate-off", action="store_true", help="DIAGNOSTIC ONLY: disable the retrieval gate")
    return parser.parse_args(argv)
```

### T14 · `pytest`: test, fixture, `parametrize`
Template:
```python
@pytest.fixture
def db_path(tmp_path):            # tmp_path is provided by pytest: a temp directory
    return tmp_path / "x.sqlite"

def test_x(db_path):              # a parameter named like a fixture is injected automatically
    assert ...
```
C#: fixture ≈ constructor/`IClassFixture` của xUnit; `parametrize` ≈ `[Theory]` + `[InlineData]`; `assert` trần (pytest viết lại để in giá trị).
Ví dụ repo:
**`tests/unit/infrastructure/test_embedding_cache.py:14-26`**
```python
@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "cache" / "embeddings.sqlite"


def test_second_call_with_same_texts_makes_no_inner_call(db_path):
    inner = FakeEmbedder()
    with CachingEmbedder(inner, db_path) as cache:
        first = cache.embed(["a", "b"], DOC)
        second = cache.embed(["a", "b"], DOC)
    assert len(inner.calls) == 1
    assert first == second
    assert cache.hits == 2 and cache.misses == 2
```
**`tests/unit/application/test_eval_latency.py:29-32`**
```python
@pytest.mark.parametrize("p", [0, -1, 100.5])
def test_nearest_rank_rejects_p_outside_0_100(p):
    with pytest.raises(ValueError):
        nearest_rank([1, 2, 3], p)
```
`with pytest.raises(ValueError):` ≈ `Assert.Throws<ValueError>(...)`.

### T15 · Test double (fake) — object giả có hành vi
Ví dụ repo: `FakeEmbedder` tạo vector giả **xác định** từ hash của văn bản, đếm số lần gọi, không dùng mạng:
**`tests/fakes.py:12-24`**
```python
class FakeEmbedder:
    """Deterministic unit vectors derived from a hash of (task, text). Counts calls; no network.

    Plans calls of at most `batch_size` texts, like a provider embedder with a count limit.
    """

    def __init__(self, dim: int = 8, model_id: str = "fake-embedder@8", batch_size: int = 10) -> None:
        self.dim = dim
        self._model_id = model_id
        self.batch_size = batch_size
        self.calls: list[tuple[list[str], EmbeddingTask]] = []

    @property
```
Đọc: `self.calls` là danh sách các lời gọi (để test khẳng định "không có lời gọi thứ hai"). Thấy `Fake*` trong test = đối tượng thay thế cho dịch vụ thật. Xem file 14.

### T16 · `any()`, `all()`, kiểm tra thành viên
Template:
```python
any(start <= pos < end for start, end in spans)   # C#: spans.Any(...)
all(v == "yes" for v in values)                    # C#: values.All(...)
```
Ví dụ repo:
**`src/knowledge_assistant/application/citation/citations.py:53-55`**
```python
def _is_marker(bracket: int, number: str, code: list[tuple[int, int]]) -> bool:
    """True if the `[number]` whose "[" is at offset `bracket` is a citation marker: n >= 1 and outside code."""
    return int(number) >= 1 and not any(start <= bracket < end for start, end in code)
```

### T17 · Truthiness và `or`/`and` làm giá trị mặc định
Template:
```python
name = user_input or "default"     # "", None, 0, [], {} are all falsy
if items:                          # a non-empty list
```
C#: `string.IsNullOrEmpty(x) ? "default" : x`. Ví dụ repo: [REPO src/knowledge_assistant/config.py:35], [REPO scripts/ask.py:215] (`out = out or sys.stdout`).

### T18 · Ba kiểu tuple/set/dict literal
Template:
```python
point = (1, 2)            # tuple (immutable)
single = (1,)             # one-item tuple: the comma is required
tags = {"a", "b"}         # set
mapping = {"a": 1}        # dict
empty_set = set()         # {} is an empty dict, not a set
```
Ví dụ repo: [REPO src/knowledge_assistant/composition.py:28] (`ARMS = ("A", "B")` là tuple), [REPO src/knowledge_assistant/config.py:105-106] (`_TRUE = {"1", "true", ...}` là set, dùng để kiểm `word in _TRUE`).

---

## Level 3 — Advanced: đọc code "khó nhìn"

### T19 · Regex có tên và lookaround
Template: `re.compile(r"(?<!x)y(?=z)")` = "y, không đứng sau x, và đứng trước z" (lookaround không tiêu thụ ký tự). Ví dụ repo: [REPO src/knowledge_assistant/application/citation/citations.py:16-23]. Cách đọc: tách regex thành cụm; đọc **tên biến** (`_FENCE_OPEN`, `_INLINE_CODE`) trước, rồi mới đến pattern; kiểm bằng test/ví dụ.

### T20 · Class với state + method + property
Ví dụ: `SlidingWindowThrottle` giữ hàng đợi `deque`, hàm `acquire` là "cổng vào":
**`src/knowledge_assistant/infrastructure/embeddings/throttle.py:40-60`**
```python
    def acquire(self, tokens: int, requests: int = 1) -> float:
        """Record one call worth `requests` quota requests; return the seconds waited for it."""
        if tokens > self._max_tokens or requests > self._max_requests:
            raise EmbeddingError(
                f"one call needs {requests} requests / ~{tokens} tokens, above the per-minute limits "
                f"{self._max_requests} / {self._max_tokens}; use a smaller batch"
            )
        waited = 0.0
        while True:
            now = self._clock()
            while self._sent and self._sent[0][0] <= now - self._window_s:
                self._sent.popleft()
            used_requests = sum(r for _, r, _ in self._sent)
            used_tokens = sum(t for _, _, t in self._sent)
            if used_requests + requests <= self._max_requests and used_tokens + tokens <= self._max_tokens:
                self._sent.append((now, requests, tokens))
                self.total_wait_s += waited
                return waited
            wait = self._sent[0][0] + self._window_s - now
            self._sleep(wait)
            waited += wait
```
Đọc bằng câu chuyện: "vào vòng lặp; xoá các lời gọi đã quá 60 giây; cộng số request/token còn trong cửa sổ; nếu còn chỗ → ghi nhận và trả về thời gian đã chờ; nếu không → tính phải ngủ bao lâu để lời gọi cũ nhất rời cửa sổ, ngủ, rồi lặp".

### T21 · Bắt rồi phân loại lỗi (error-boundary)
Đọc `gemini_llm.py:184-202`: một hàm gọi thư viện ngoài, bắt tập lỗi của nhà cung cấp (`PROVIDER_ERRORS` là một **tuple** các class), phân loại, gọi hook quan sát trong `try/except` riêng, rồi **trả** một object mô tả thất bại thay vì ném:
**`src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py:184-202`**
```python
    def _attempt(self, client: Any, model: str, request: LLMRequest, config: Any, tally: _Tally) -> _Attempt:
        tally.throttle_wait_s += self._throttles[model].acquire(0)
        self.requests += 1
        self.requests_by_model[model] = self.requests_by_model.get(model, 0) + 1
        start = self._clock()
        try:
            response = client.models.generate_content(model=model, contents=request.prompt, config=config)
        except PROVIDER_ERRORS as error:
            failure = classify_failure(error)
            if failure.status == 429 and not self._logged_first_429:
                self._logged_first_429 = True
                logger.warning("first HTTP 429 of this run (model %s), raw error body: %s", model, failure.body)
            if self._on_provider_error is not None:
                try:
                    self._on_provider_error(model, failure)
                except Exception as hook_error:  # the observer must never change retry, fallback or the raised error
                    logger.warning("provider-error hook failed (%s); continuing", type(hook_error).__name__)
            return _Attempt(failure=failure, error=error, config=config)
        return _Attempt(response=response, latency_ms=(self._clock() - start) * 1000.0, config=config)
```
Điểm cần để ý khi đọc: `except PROVIDER_ERRORS as error` (bắt nhiều class một lúc); return sớm trong `except`; dòng cuối là đường hạnh phúc.

### T22 · Nhận diện "đọc bảng tra" thay cho switch
Ví dụ: `_ERROR_TITLE.get(kind, "Could not get an answer")` = tra dict, không có thì dùng mặc định: [REPO src/knowledge_assistant/presentation/desktop/viewmodels/ask_viewmodel.py:89-94]. C#: `dict.TryGetValue(kind, out var v) ? v : "..."`.

---

## Trace bằng đầu (drills, đáp án đã chạy thử offline)

**Drill 1 — `dedupe_by_passage`.** Đọc [REPO src/knowledge_assistant/application/retrieval/retrieve.py:29-45]. Có 4 hit (chunk_id, score, passage): `("c1", 0.9, "P")`, `("c2", 0.8, "P")`, `("c4", 0.7, "R")`, `("c3", 0.7, "Q")`, `top_k = 2`. Kết quả (id, rank, duplicate_chunk_ids) và số bị bỏ?
<details><summary>Đáp án</summary>
Sắp theo (−score, chunk_id): c1, c2, c3, c4 (c3 trước c4 vì hoà điểm và "c3" < "c4"). c1 giữ (passage P); c2 cùng passage P → ghi vào `replaced`, không giữ; c3 giữ (Q); c4 giữ trong dict (R). `dropped = len(ordered) − len(kept) = 4 − 3 = 1`. Cắt còn 2: `[("c1", rank 1, ("c2",)), ("c3", rank 2, ())]`, dropped = 1 (đã chạy thử).
</details>

**Drill 2 — `excerpt`.** [REPO src/knowledge_assistant/application/citation/citations.py:74-85]: `excerpt("word " * 100, 22)` trả về gì và vì sao không cắt giữa từ?
<details><summary>Đáp án</summary>
`"word word word word"` (19 ký tự). `cut = text[:22]` = `"word word word word wo"`; ký tự thứ 22 là `r` (không phải khoảng trắng) nên lùi về khoảng trắng cuối bằng `rfind(" ")` (vị trí 19) và cắt tại đó. Kết quả luôn là tiền tố **nguyên văn** của text, không thêm dấu "…", để tìm lại được trong chunk (docstring).
</details>

**Drill 3 — `SlidingWindowThrottle`.** Throttle `(3, 1000, 60.0)` với đồng hồ giả bắt đầu 0; gọi `acquire(10)` 4 lần. `estimate_tokens("abcdefghi")` và `estimate_tokens("")`?
<details><summary>Đáp án</summary>
Chờ `[0.0, 0.0, 0.0, 60.0]`. `estimate_tokens("abcdefghi")` = `ceil(9/4)` = 3; `estimate_tokens("")` = `max(1, ceil(0/4))` = 1 ([REPO src/knowledge_assistant/infrastructure/embeddings/throttle.py:13-14]).
</details>

**Drill 4 — `_embed_and_store` (chỉ đọc).** [REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:144-162]. Trả lời: (a) khi nào ném `EmbeddingError`? (b) vì sao `stored[key]` được tạo bằng `_from_blob(blob, ...)` chứ không dùng trực tiếp `vector`? (c) `with self._db:` làm gì?
<details><summary>Đáp án</summary>
(a) khi số vector trả về khác số text (`len(vectors) != len(texts)`). (b) để giá trị trả về ở lần **miss** giống hệt giá trị đọc lại từ cache ở lần **hit** (đều qua float32) — kết quả không phụ thuộc trạng thái cache (comment dòng 159). (c) mở một transaction SQLite: `executemany` INSERT tất cả rows của một lần gọi provider, commit khi ra khỏi khối (rollback nếu lỗi) — "một transaction cho mỗi lần gọi provider" (comment dòng 160).
</details>

---

## Exercises bổ sung (đọc-hiểu, offline)
- **E1 (B):** Với bảng 1.3, tự đọc ra ý nghĩa của mọi ký hiệu trong [REPO src/knowledge_assistant/application/evaluation/stats.py:63-64] (chữ ký `paired_bootstrap_ci`).
  <details><summary>Gợi ý</summary>`a: list[float]`, `b: list[float]` là hai mẫu ghép cặp; `resamples: int = BOOTSTRAP_RESAMPLES` có mặc định 10 000; `statistic=_mean` truyền **hàm** làm tham số (mặc định là trung bình); trả `BootstrapResult` (dataclass).</details>
- **E2 (I):** Tìm trong repo 3 chỗ dùng `x if c else y`; viết lại bằng `if/else` thường (chỉ trên giấy).
- **E3 (A):** Chọn một hàm bất kỳ trong `src/knowledge_assistant/application/` (không dùng hàm đã có trong file này). Áp quy trình 6 bước ở mục 1.1 và viết 3 câu: hàm làm gì, đầu vào/ra, một điều có thể sai.

## Self-check questions
1. Dòng `first, *rest = xs` làm gì? Còn `*complete, tail = ...`?
2. `sorted(items, key=lambda it: (-it.score, it.id))` sắp theo thứ tự nào?
3. `with x:` và `with x as y:` khác gì? Khi nào `x` có `__enter__`/`__exit__`?
4. `args.gate_off` đến từ đâu nếu tham số là `--gate-off`?
5. Trong pytest, làm sao một hàm test "nhận" `tmp_path` mà không ai truyền vào?

## Interview Q&A
1. **"Bạn đọc code Python lạ như thế nào?"** — Docstring → import → hằng số/kiểu → hàm công khai → chạy bằng đầu một ví dụ nhỏ; dùng test làm ví dụ sống.
2. **"Decorator là gì?"** — Hàm nhận hàm và trả hàm; repo dùng decorator chuẩn như `@dataclass`, `@property`, `@contextmanager`, `@pytest.fixture` (mục T9).
3. **"Khác biệt `is None` và `== None`?"** — `is` so sánh danh tính, là cách chuẩn với `None` ([REPO src/knowledge_assistant/presentation/desktop/viewmodels/ask_viewmodel.py:105]).
4. **"Vì sao test dùng fake thay vì gọi API thật?"** — Xác định, miễn phí, không cần mạng/key; repo có `FakeEmbedder`, `FakeClock`, `FakeLLM`... ([REPO tests/fakes.py:12-62]).

## Further reading
- Python Tutorial (docs.python.org): *More Control Flow Tools*, *Data Structures*, *Modules*, *Classes*. `[GENERAL]`
- pytest docs: *How to use fixtures*, *parametrize*. `[GENERAL]`
- Tiếp theo: [03 — Kiến trúc](03-architecture-and-gui.md).
