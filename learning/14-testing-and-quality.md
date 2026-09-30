# 14 · Kiểm thử và chất lượng: pytest, fake tự viết, bộ test offline, test không ổn định (flaky), mutation testing
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [01](01-python-for-csharp-devs.md), [02](02-python-tooling-and-dependencies.md), [03](03-architecture-and-gui.md), [04](04-data-io-and-reliability-patterns.md), [09](09-llm-api-engineering.md) · Study time: ~7–9h · Home file của: pytest (`assert`, fixture, `tmp_path`, `monkeypatch`, `pytest.raises`, `parametrize`), fake vs mock, `tests/fakes.py` (`FakeClock`, `FakeEmbedder`, `FakeModels`, `api_error`, `FakeLLM`), test offline mặc định, test flaky, mutation testing thủ công, kỷ luật "không báo thành công khi chưa kiểm"
> Bài tập chạy được: `learning/_tools/exercises/mutation_demo.py <thư-mục-tạm>` (sao chép `src`/`tests` ra thư mục tạm **ngoài repo**, phá một dòng có chủ đích, chạy test ở đó). Offline, không mạng, không key.

## Vì sao file này quan trọng trong dự án
Một dự án gọi API đắt tiền và không ổn định **không thể** kiểm thử bằng cách gọi API. Repo giải bằng cách: mọi bộ chuyển đổi (adapter) nằm sau một interface, và test dùng **fake tự viết** thay cho Gemini/Chroma/đồng hồ. Kết quả: **866 test chạy offline trong ~13 giây, không cần key, không cần mạng**. Ngoài ra dự án dùng một kỹ thuật nghiêm túc hơn cả coverage: **mutation testing** — cố tình phá code để chứng minh test thực sự bắt được lỗi. CLAUDE.md nói thẳng: "MUST NOT report success for unverified checks". [REPO CLAUDE.md:12]

---

## Level 1 — Basic

### 1.1 pytest cơ bản: hàm `test_*`, `assert` trần, fixture
- **Ý tưởng:** pytest tự tìm file `test_*.py` và hàm `test_*`, chạy từng cái; **`assert` thường** (không cần `Assert.Equal`) — khi sai pytest tự in giá trị hai vế. **Fixture** là hàm cung cấp dữ liệu/tài nguyên cho test, tiêm vào qua **tên tham số**.
- **Trong repo này:**
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
- **Đọc chậm:** `@pytest.fixture def db_path(tmp_path)` — fixture `db_path` **tự nhận** fixture có sẵn `tmp_path` (một thư mục tạm riêng cho mỗi test, pytest dọn sau). Test `test_second_call_with_same_texts_makes_no_inner_call(db_path)` nhận `db_path` chỉ bằng cách đặt tên tham số. Ba `assert` đơn giản kiểm: lời gọi bên trong đúng **một** lần, kết quả hai lần **giống nhau**, và đếm `hits`/`misses`.
- **Tên test là đặc tả:** `test_second_call_with_same_texts_makes_no_inner_call` đọc như một câu hành vi. Đây là quy ước của cả bộ test. [REPO tests/unit/infrastructure/test_embedding_cache.py:19-27]
- **C# analogy:** xUnit `[Fact]` ↔ hàm `test_*`; `[Theory]/[InlineData]` ↔ `@pytest.mark.parametrize`; fixture ↔ `IClassFixture<T>`/constructor của class test; `Assert.Throws<T>` ↔ `pytest.raises(T)`; `Path.GetTempPath()` ↔ `tmp_path`.
- **Số liệu thật (đã chạy, một lần, trên worktree ở commit ghim):** `866 passed, 1 deselected in 13.27s`, exit 0 — khớp với README. Repo có **69 file** dưới `tests/`; `git grep` đếm **686** dòng `def test_` (ít hơn 866 vì `parametrize` nhân một hàm thành nhiều test), khoảng 276 lần dùng `tmp_path`, 80 `monkeypatch`, 114 `pytest.raises`, 49 `parametrize`, 13 `fixture`. [REPO README.md:129-129] (Các số đếm là số **dòng khớp** từ `git grep`, không phải số test.)
- **Tại sao gọi `python -m pytest`:** dùng đúng interpreter/`sys.path` (file 02 §3.1).
- **Pitfalls `[GENERAL]`:** `assert` với float cần `pytest.approx`; và pytest **viết lại** câu `assert` để in chi tiết nên đừng dùng `assert (a, b)` (tuple luôn đúng).

### 1.2 Offline theo mặc định, marker `gemini` cho ngoại lệ
- **Quy tắc:** test mặc định **offline**; test cần key thật dùng `@pytest.mark.gemini` và bị loại bởi `addopts = "-m 'not gemini'"`. [REPO CLAUDE.md:12], [REPO pyproject.toml:25-31]
- **Số liệu:** "1 deselected" trong kết quả chính là test live duy nhất (`tests/integration/retrieval/test_gemini_embedding_live.py`). [REPO tests/integration/retrieval/test_gemini_embedding_live.py:30-30]
- **Tại sao:** mỗi lần chạy test không được tốn quota/tiền; và kết quả không phụ thuộc mạng. **Trong buổi soạn tài liệu này** tôi cũng chỉ chạy bộ offline.
- **Pitfalls `[GENERAL]`:** offline **không** chứng minh tích hợp thật hoạt động; nó chứng minh **logic** của bạn đúng khi phía ngoài hành xử như đã giả lập. Vì vậy repo vẫn có smoke check live có ghi chú (`validation/generation/smoke-*.md`) — nhưng **không** dùng làm dữ liệu đánh giá.

### 1.3 Fake, stub, mock: phân biệt
- **Stub:** trả giá trị cố định. **Fake:** cài đặt **thật nhưng đơn giản** (ví dụ vector store trong bộ nhớ). **Mock:** ghi lại lời gọi và **kiểm tra tương tác** (thường bằng thư viện).
- **Trong repo:** hầu hết là **fake viết tay** trong `tests/fakes.py` (không dùng thư viện mock cho phần lõi) — dễ đọc, dễ tái sử dụng, và có thể **kịch bản hoá** thất bại.
- **C# analogy:** thay vì `Mock<IEmbedder>().Setup(...)` (Moq), bạn viết `class FakeEmbedder : IEmbedder` dùng lại ở hàng trăm test.
- **Tại sao:** vì kiến trúc có `Protocol`/interface (file 03), thay thế bằng fake chỉ là truyền một object khác vào constructor — không cần "patch" gì cả.
- **Pitfalls `[GENERAL]`:** fake quá thông minh có thể **có lỗi riêng** và che lỗi thật; giữ fake nhỏ và test hành vi quan trọng của chính nó nếu cần.

---

## Level 2 — Intermediate

### 2.1 Bộ fake của repo: đọc như một danh mục kỹ thuật
Mọi fake nằm ở `tests/fakes.py`:
| Fake | Thay cho | Điểm hay |
|---|---|---|
| `FakeEmbedder` | `Embedder` (Gemini) | vector **xác định** từ hash `(task, text)`; đếm lời gọi; chia lô như embedder thật |
| `FakeClock` | thời gian + `sleep` | `sleep` **dịch chuyển** thời gian → test throttle/backoff chạy tức thì |
| `FakeModels` | `client.models` của SDK | **kịch bản lỗi**: danh sách exception ném lần lượt; `fail_from_call` |
| `api_error(code, retry_delay, quota_id)` | lỗi HTTP của Google | dựng đúng **hình dạng body** `google.rpc` (RetryInfo, QuotaFailure) |
| `InMemoryVectorStore` | Chroma | điểm bằng tích vô hướng, ghi đè điểm để **kịch bản hoá** thứ hạng và hoà |
| `FakeLLM` | Gemini `generate` | trả lần lượt các text kịch bản, ghi lại mọi request |
- **Đọc `FakeClock` và `FakeLLM`:**
**`tests/fakes.py:50-62`**
```python
class FakeClock:
    """One clock for the throttle and every sleep: sleeping moves time forward."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds
```
**`tests/fakes.py:187-200`**
```python
class FakeLLM:
    """LLM double: returns the scripted texts in order (the last one repeats) and records every request."""

    def __init__(self, *texts: str, model: str = "fake-llm") -> None:
        self.texts = list(texts)
        self.model = model
        self.requests: list = []

    def generate(self, request):
        from knowledge_assistant.core.interfaces.llm import LLMResponse

        self.requests.append(request)
        text = self.texts[min(len(self.requests), len(self.texts)) - 1]
        return LLMResponse(text=text, model_used=self.model, retry_count=0, fallback_used=False,
```
- **Đọc chậm:** `FakeClock.__call__` cho phép **gọi như hàm** (`clock()`) — object có `__call__` được dùng ở chỗ cần `Callable[[], float]` (đúng kiểu tham số `clock` ở file 08 §1.2). `sleep` cộng thời gian: nhờ đó `retry` của `GeminiLLM` chạy hết 3 lần trong micro-giây nhưng vẫn **ghi lại** đã ngủ bao lâu (`clock.sleeps`). `FakeLLM(*texts)` là **varargs**; `self.texts[min(len(self.requests), len(self.texts)) - 1]` lấy text thứ `n` và **lặp lại text cuối** khi hết.
- **Đã chạy thử offline** (bộ kịch bản ở file 09, `llm_retry_scenarios.py`): cùng các fake này dựng 7 kịch bản retry/fallback (ngủ `1.5` và `2.5`, fallback, lỗi 400 không fallback...) mà không đụng mạng.
- **Tại sao `api_error` dựng đúng body:** code phân loại lỗi (`classify_failure`, file 09) đọc `RetryInfo`/`QuotaFailure` từ body; nếu fake chỉ ném `Exception("429")` thì test **không kiểm** phần phân loại. Độ trung thực của fake quyết định độ tin cậy của test. [REPO tests/fakes.py:101-118]
- **Pitfalls `[GENERAL]`:** fake sai so với thật cho kết quả xanh giả; vì vậy `api_error` bám đúng hình dạng trong tài liệu API — và code ghi thẳng rằng một số hình dạng "not yet seen in a real response" (file 09 §2.3).

### 2.2 Test hành vi mất điện/hỏng giữa chừng bằng fake có kịch bản
Test dưới đây kiểm điều mà file 04 §2.5 mô tả: embedder **ném lỗi ở lời gọi thứ ba**, và các nhóm đã trả tiền vẫn được lưu:
**`tests/unit/infrastructure/test_embedding_cache.py:46-64`**
```python
def test_misses_are_sent_in_batches_and_each_batch_is_stored(db_path):
    class FailsOnThirdCall(FakeEmbedder):
        def embed(self, texts, task):
            if len(self.calls) == 2:
                raise EmbeddingError("quota")
            return super().embed(texts, task)

    inner = FailsOnThirdCall(batch_size=2)
    with CachingEmbedder(inner, db_path) as cache:
        with pytest.raises(EmbeddingError):
            cache.embed(["1", "2", "3", "4", "5"], DOC)
    assert [len(texts) for texts, _ in inner.calls] == [2, 2]

    resumed = FakeEmbedder(batch_size=2)
    with CachingEmbedder(resumed, db_path) as cache:
        cache.embed(["1", "2", "3", "4", "5"], DOC)
    assert resumed.calls == [(["5"], DOC)]


```
- **Đọc chậm:** class `FailsOnThirdCall(FakeEmbedder)` được **định nghĩa ngay trong test** (kế thừa, ghi đè `embed`); `with pytest.raises(EmbeddingError):` khẳng định lỗi **phải** ném; `[len(texts) for texts, _ in inner.calls] == [2, 2]` khẳng định hai lời gọi đã thực hiện; phần sau tạo embedder mới với **cùng file DB** và khẳng định `resumed.calls == [(["5"], DOC)]` — chỉ text `5` bị gửi lại.
- **Đã chạy thử offline** (file 04, mục C4): kịch bản tương tự cho `2 hits, 3 misses` và chỉ gửi `[t3,t4]`, `[t5]`.
- **Tại sao chọn kiểm thử theo *hành vi quan sát được* (`resumed.calls`) thay vì nội bộ (`self._db`):** test còn đúng khi bạn đổi cách cài đặt bên trong.
- **Torn write cũng có test riêng:**
**`tests/unit/infrastructure/test_jsonl_record_store.py:60-71`**
```python
def test_an_unterminated_last_line_is_not_a_record_and_the_next_append_drops_it(tmp_path):
    """A process killed mid-write leaves a torn tail. It must neither crash a resume nor swallow the next record."""
    store = _store(tmp_path)
    store.append_record({"case_id": "Q-T-1"})
    store.append_record({"case_id": "Q-T-2"})
    with (tmp_path / "run-1" / "records.jsonl").open("ab") as handle:
        handle.write(b'{"case_id": "Q-T-3", "sta')  # no newline: the write was cut off
    assert [record["case_id"] for record in store.read_records()] == ["Q-T-1", "Q-T-2"]
    store.append_record({"case_id": "Q-T-3"})
    assert [record["case_id"] for record in store.read_records()] == ["Q-T-1", "Q-T-2", "Q-T-3"]
    assert (tmp_path / "run-1" / "records.jsonl").read_bytes().count(b"\n") == 3  # the torn fragment is gone

```
  Test này mô phỏng chính xác tiến trình bị kill giữa lúc ghi (`b'{"case_id": "Q-T-3", "sta'`, không có `\n`) rồi khẳng định (1) đọc không lỗi, (2) lần append sau **cắt** mảnh cụt, (3) file kết thúc gọn với 3 dấu `\n`. Đây là "chứng cứ thực thi" cho khẳng định docstring của store. [REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:4-6]
- **C# analogy:** `Assert.ThrowsAsync<...>` + một `IEmbedder` giả ném ở lời gọi thứ 3.

### 2.3 `monkeypatch` và `tmp_path`: tách môi trường của mỗi test
- **`monkeypatch`:** đặt/xoá biến môi trường, thuộc tính, `sys.path` **chỉ trong phạm vi test** rồi tự khôi phục. Ví dụ ở test biên giới Gemini: xoá `GEMINI_API_KEY` và khẳng định adapter ném `ConfigurationError` với `requests == 0`. [REPO tests/unit/test_gemini_boundary.py:8-13]
- **`tmp_path`:** dùng ~276 lần trong các test; mỗi test có thư mục riêng, không đụng repo (đây là lý do bộ test **không để lại file** trong cây làm việc — kiểm ở đầu buổi: sau khi chạy 866 test, `git status --ignored` vẫn không có gì ngoài `learning/`).
- **Tại sao quan trọng:** test độc lập nhau, chạy theo thứ tự nào cũng được, và **không** phá dữ liệu thật (ví dụ `data/chroma`).
- **Pitfalls `[GENERAL]`:** test phụ thuộc thứ tự chạy (chia sẻ trạng thái toàn cục) là nguồn của test flaky (3.1).

### 2.3b Phạm vi fixture và `autouse`
- **`scope="module"`:** mặc định fixture được dựng lại cho **mỗi test**; `@pytest.fixture(scope="module")` dựng **một lần cho cả file** — phù hợp việc tốn kém như nạp một script bằng `importlib` (ví dụ `script` trong test của `normalize_corpus`). [REPO tests/unit/application/test_normalize_corpus.py:27-32]
- **`autouse=True`:** fixture chạy cho **mọi test trong file mà không cần khai báo tham số**; ở `test_ask_cli.py` nó đặt biến môi trường `LOGS_DIR` trỏ vào `tmp_path` bằng `monkeypatch`, nên **không test nào** vô tình ghi log vào thư mục dữ liệu thật:
**`tests/unit/test_ask_cli.py:61-63`**
```python
@pytest.fixture(autouse=True)
def logs_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))
```
- **C# analogy:** `IClassFixture<T>` (một lần cho cả class) so với constructor của class test (mỗi test một lần); `autouse` giống một bước `SetUp` áp cho mọi test.
- **Pitfalls `[GENERAL]`:** fixture phạm vi rộng chia sẻ trạng thái giữa các test — nếu test sửa nó, test sau bị ảnh hưởng; dùng cho dữ liệu **chỉ đọc**.

### 2.4 Test theo bảng: `parametrize`
- **Ý tưởng:** một hàm test, nhiều bộ dữ liệu; mỗi bộ thành một test riêng trong báo cáo. Đây là một lý do 686 dòng `def test_` mở rộng thành 866 test (`[GENERAL]` suy luận: các kịch bản `parametrize` nhiều tham số nhân số test).
- **Trong repo này** (test của `AnswerQuestion`, file 08): năm chuỗi đầu ra hỏng của LLM, **một** hàm test:
**`tests/unit/application/test_answer_question.py:103-113`**
```python
@pytest.mark.parametrize("raw", [
    "not json at all",
    '{"insufficient": false, "answer": "x"}',  # keys missing
    '{"insufficient": "no", "answer": "x", "cited_passages": [], "missing_information": ""}',
    '{"insufficient": false, "answer": "  ", "cited_passages": [], "missing_information": ""}',
    '["a list"]',
])
def test_unusable_llm_output_raises_generation_error_with_raw_text(raw):
    with pytest.raises(GenerationError) as caught:
        _service(FakeLLM(raw)).ask("Question?")
    assert caught.value.raw_text == raw
```
- **Đọc chậm:** decorator `@pytest.mark.parametrize("raw", [...])` chạy hàm **năm lần**, mỗi lần `raw` là một phần tử; `pytest.raises(GenerationError) as caught` bắt ngoại lệ vào `caught`, rồi `caught.value.raw_text == raw` khẳng định lỗi **giữ nguyên văn** đầu ra hỏng (đúng như `parse_answer_json` ở file 08 §1.5). Một test khác tham số hoá **ba loại lỗi LLM** để khẳng định "lỗi API không bao giờ bị biến thành insufficient". [REPO tests/unit/application/test_answer_question.py:162-171]
- **C# analogy:** `[Theory]` + `[InlineData("A [1].", 1)]`.
- **Tại sao:** bảng dữ liệu cho phép thêm ca biên rẻ; báo cáo chỉ đúng ca nào fail.
- **Pitfalls:** đặt `ids=` cho các tham số dài để báo cáo đọc được; đừng nhét logic điều kiện vào thân test.

---

## Level 3 — Advanced

### 3.1 Test flaky: khi một test "đôi khi" fail
- **Sự thật `[REAL]` trong repo:** `test_top_k_larger_than_the_collection_returns_everything` (`tests/unit/infrastructure/test_chroma_store.py`) fail **một lần** trong lượt chạy full-suite với `InternalError: Error in compaction`. QC-001 chạy lại 5 lần riêng, 5 lần cả module, 5 lần cả bộ 866 test: **15/15 pass, 0 tái hiện**. Nguyên nhân gốc **chưa xác định**; nghi ngờ vấn đề thời điểm bên trong HNSW/compaction của chromadb nhưng **chưa được xác nhận**. Repo **để nguyên** và ghi vào README như hạn chế đã biết. [REPO README.md:305-309]
- **Trong buổi này (kiểm độc lập):** bộ đầy đủ chạy **1 lần**: 866 passed (không thấy flaky). Đây là **một** quan sát; nó không chứng minh test hết flaky.
- **Bài học kỹ thuật:**
  1. **Đừng che flaky bằng retry/skip** mà không ghi lại; ghi nhận trung thực (như README).
  2. **Thu thập bằng chứng có hệ thống** (15 lần chạy ở ba phạm vi) thay vì kết luận từ một lần.
  3. Phân biệt **flaky do test** (thứ tự, thời gian) và **do thư viện** (ở đây nghi ngờ thư viện).
- **C# analogy:** test `[Fact]` thỉnh thoảng đỏ do đua luồng/thời gian; cách xử lý chuẩn: cô lập, lặp, ghi lại, sửa gốc.
- **Pitfalls `[GENERAL]`:** "chạy lại là xanh" là **thói quen nguy hiểm** — nó làm bạn tin dữ liệu sai. Trung thực về sự không chắc chắn (như README) tốt hơn.

### 3.2 Mutation testing thủ công: kiểm chính **bộ test**
- **Ý tưởng:** coverage chỉ nói dòng nào **được chạy**, không nói test có **bắt lỗi** hay không. *Mutation testing*: cố tình **phá một dòng** (ví dụ bỏ điều kiện, đổi toán tử) rồi chạy test; nếu test **vẫn xanh**, đột biến "sống sót" → test yếu hoặc dòng đó không quan sát được. Repo làm việc này **thủ công** ở nhiều tác vụ (báo cáo ghi "mutation … fails N tests").
- **Đã chạy thật** (`mutation_demo.py`, trên **bản sao ngoài repo**; kết quả một lần chạy):
  | Đột biến | Kết quả | Ý nghĩa |
  |---|---|---|
  | M0 không đổi (đối chứng) | `13 passed` | bộ test xanh trước khi phá |
  | M1 khoá cache **bỏ `task`** (`f"{model_id}|{text}"`) | `2 failed, 11 passed` | `test_task_and_model_id_are_part_of_the_key` và `test_missing_lists_unique_uncached_texts_without_calling_the_inner_embedder` **bắt được** |
  | M2 **bỏ `truncate`** đuôi cụt | `1 failed, 8 passed` | `test_an_unterminated_last_line_is_not_a_record_and_the_next_append_drops_it` bắt được |
  | M3 **bỏ `os.fsync`** | `9 passed` (không fail) | đột biến **sống sót** |
- **Đọc chậm M3:** không test nào phát hiện việc bỏ `fsync` vì **không thể quan sát** `fsync` từ chương trình trong một tiến trình (chỉ khác biệt khi mất điện thật). Đây là **đột biến tương đương hoặc không kiểm được** — bạn ghi nhận nó như một **giới hạn có chủ ý**, không cố "viết test cho được". Bài học: mutation testing chỉ ra chỗ test **không** phủ, và có chỗ không thể phủ.
- **Cách chạy tương tự (không cần công cụ):** sao chép cây làm việc ra thư mục tạm, sửa một dòng bằng thay chuỗi **có kiểm tra khớp**, chạy `pytest` ở đó, rồi xoá. Script làm đúng thế và in "MUTATION DID NOT APPLY" khi mẫu không khớp (tránh kết luận sai).
- **Sự cố `[REAL]` #1 — đột biến bị bỏ sót:** ở INGEST-001, AI khôi phục file đã đột biến bằng `git checkout` nhưng file **chưa được theo dõi** nên lệnh không làm gì; "excluded-document guard" vẫn là `if False:`. Phát hiện nhờ `grep` lại file sau bước khôi phục, **trước khi commit**. Bài học: **kiểm chứng việc khôi phục**, không chỉ việc phá. [REPO AI_WORKLOG.md:129-131]
- **Sự cố `[REAL]` #2 — đột biến "không khớp":** ở INGEST-003, đột biến BOM đầu tiên "sống sót" vì mã nguồn chứa **ký tự BOM vô hình** nên `sed` không khớp; phát hiện bằng `cat -A`, thay bằng chuỗi thoát `﻿`, rồi đột biến làm fail 1 test. Bài học: một đột biến "sống sót" có thể do **đột biến không được áp dụng**. [REPO AI_WORKLOG.md:161-161]
- **Đo bằng mutation ở các tác vụ đánh giá:** ví dụ `RAG-002 fix F1`: tắt bỏ qua code → 7 test fail; tắt luật `[0]` → 3 test fail (file 08 §3.1). [REPO AI_WORKLOG.md:351-352]
- **Tại sao:** dự án dùng mutation làm **cổng nghiệm thu** cho phần đánh giá (kết quả không bịa được nếu test bắt lỗi thật). Đây là kỷ luật cao hơn "tỉ lệ coverage".
- **Pitfalls `[GENERAL]`:** công cụ mutation tự động (ví dụ `mutmut`, `cosmic-ray` cho Python) phá hàng loạt; nhưng chạy chậm và sinh nhiều đột biến tương đương. Thủ công có chủ đích, ở chỗ **quan trọng**, thường hiệu quả hơn.

### 3.3 Kiểm thử kiến trúc: một test bằng `ast` ép quy tắc tầng
- **Đã chi tiết ở file 03** (`tests/unit/test_project_structure.py`, 9 test; và hai đột biến đã chạy trên bản sao ngoài repo, đều làm fail đúng test mong đợi). Ở đây chỉ nhắc: quy tắc "core không import PySide6/Chroma/Gemini" được **kiểm bằng máy**, không bằng lời hứa. [REPO CLAUDE.md:7]
- **Tại sao:** ràng buộc kiến trúc mà không có test sẽ mục nát khi có thêm người/tác nhân sửa code.

### 3.4 Thiết kế test cho code khó test: bốn kỹ thuật lặp lại trong repo
1. **Tiêm phụ thuộc** để thay bằng fake (mọi adapter sau `Protocol`).
2. **Tiêm đồng hồ và `sleep`** (`clock=`, `sleep=`, `jitter=`) để thời gian **xác định** (file 08–09).
3. **Fake có kịch bản thất bại** (`script`, `fail_from_call`, `FailsOnThirdCall`) để kiểm đường lỗi, thứ khó xảy ra ở môi trường thật.
4. **Kiểm hành vi quan sát được** (`resumed.calls`, nội dung file) thay vì trạng thái nội bộ.
- **C# analogy:** `TimeProvider`/`ISystemClock`, `IHttpClientFactory` với `HttpMessageHandler` giả — cùng ý.
- **Tại sao:** đường lỗi (429, 503, mất điện) hiếm khi tự xảy ra khi test; bạn phải **tạo ra** chúng bằng fake.

### 3.5 Kỷ luật báo cáo: không nói "xong" khi chưa kiểm
- **Quy tắc:** "MUST NOT report success for unverified checks." [REPO CLAUDE.md:12] Trong repo điều đó thể hiện ở: báo cáo tác vụ có mục "Unverified/open", verifier độc lập chạy lại số liệu, và README ghi hạn chế (một test flaky, chưa chạy trên Linux).
- **Trong buổi này:** những gì tôi đã **chạy thật** được ghi là "đã chạy"; những gì chỉ suy luận thì gắn `[GENERAL]`/`[UNVERIFIED]`. Ví dụ: 866 test đã chạy **một lần** trên Windows; **chưa** chạy trên Linux.
- **Tại sao:** độ tin cậy của một báo cáo nằm ở việc phân biệt **đã kiểm** và **suy đoán**.

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Vì sao `db_path` là fixture nhận `tmp_path` thay vì dùng thẳng một đường dẫn cố định?
<details><summary>Đáp án</summary>
Mỗi test cần một file DB **riêng và sạch** để không ảnh hưởng nhau và không đụng dữ liệu thật; `tmp_path` cấp thư mục tạm mới cho mỗi test và pytest tự dọn ([REPO tests/unit/infrastructure/test_embedding_cache.py:14-16]).
</details>

**B2 (Basic).** Điều gì khiến bộ test mặc định không gọi API thật?
<details><summary>Đáp án</summary>
Marker `gemini` + `addopts = "-m 'not gemini'"` (loại test live), cộng với việc mọi adapter được thay bằng fake trong test ([REPO pyproject.toml:28-31]).
</details>

**B3 (Basic).** Khác nhau giữa fake và mock? Repo dùng cái nào cho `Embedder`?
<details><summary>Đáp án</summary>
Fake là cài đặt đơn giản nhưng hoạt động thật (vector xác định từ hash); mock ghi lại và kiểm tra tương tác. Repo dùng **fake viết tay** (`FakeEmbedder`) và tái sử dụng ở nhiều test ([REPO tests/fakes.py:12-47]).
</details>

**I1 (Intermediate).** Viết (giấy) test cho hành vi "cùng text nhưng khác task là hai entry cache khác nhau" — cần fake gì và khẳng định gì?
<details><summary>Đáp án</summary>
Dùng `FakeEmbedder` và `CachingEmbedder(inner, db_path)`; gọi `embed(["a"], DOC)` rồi `embed(["a"], QUERY)`; khẳng định `len(inner.calls) == 2` (hai lời gọi, không phải một) và `cache.misses == 2`. Đây đúng là hành vi mục C3 (file 04) đã chạy: `same text, other task is a miss`. Đột biến M1 phá đúng hành vi này và làm 2 test fail.
</details>

**I2 (Intermediate).** Dùng `mutation_demo.py`: vì sao M3 (bỏ `fsync`) không làm test nào fail? Bạn kết luận gì?
<details><summary>Đáp án</summary>
`fsync` chỉ khác biệt khi mất điện/kill hệ điều hành thật; trong một tiến trình test không thể quan sát được. Đột biến sống sót không phải lỗi của test mà là **giới hạn không kiểm được**; ghi nhận như quyết định thiết kế thay vì cố ép test.
</details>

**I3 (Intermediate).** `FakeClock.sleep` cộng thời gian thay vì ngủ thật. Điều đó cho phép kiểm điều gì về throttle mà test dùng `time.sleep` thật không làm được (hoặc làm rất chậm)?
<details><summary>Đáp án</summary>
Kiểm **chính xác** chuỗi thời gian chờ (`clock.sleeps`) và thứ tự lời gọi mà không chờ thật: ví dụ throttle `(3 request, 60s)` chờ `[0,0,0,60]` (file 01 §2.3) chạy trong micro-giây, có thể lặp hàng nghìn lần và **xác định** ([REPO tests/fakes.py:50-62]).
</details>

**A1 (Advanced).** Một đột biến "sống sót" có ba khả năng. Liệt kê và nêu cách phân biệt.
<details><summary>Đáp án</summary>
(1) **Test yếu** — thiếu ca kiểm dòng đó (viết thêm test). (2) **Đột biến tương đương/không quan sát được** (như `fsync`) — ghi nhận. (3) **Đột biến không được áp dụng** (mẫu không khớp, như trường hợp BOM vô hình) — kiểm bằng cách xác nhận file thực sự đổi (`diff`, `grep`, `cat -A`) trước khi kết luận. `mutation_demo.py` in "MUTATION DID NOT APPLY" để bắt (3) ([REPO AI_WORKLOG.md:161-161]).
</details>

**A2 (Advanced).** Bạn thấy một test fail một lần trong CI rồi xanh khi chạy lại. Nêu quy trình xử lý theo tinh thần repo và điều **không** nên làm.
<details><summary>Đáp án</summary>
Ghi lại nguyên văn lỗi và bối cảnh; chạy lặp có hệ thống ở nhiều phạm vi (riêng, cả module, cả bộ; repo dùng 5+5+5 = 15 lần); nếu không tái hiện, **ghi nhận trung thực** là hạn chế đã biết với nguyên nhân nghi ngờ nhưng chưa xác nhận. Không nên: xoá/skip test, thêm retry che giấu, hoặc tuyên bố "đã sửa" khi chưa có nguyên nhân ([REPO README.md:305-309]).
</details>

**A3 (Advanced).** Thiết kế fake cho `LLM` để kiểm test "fallback chỉ đúng một lần": cần hành vi gì, khẳng định gì?
<details><summary>Đáp án</summary>
Fake `LLM`/`client.models` với **kịch bản** `[503, 503, 503, 503]` cho mọi model; khẳng định: model chính được gọi đúng 3 lần, model dự phòng đúng **1** lần, kết quả là `LLMUnavailableError`, và **tổng lần gọi = 4**. Chính là kịch bản C ở file 09 (`503 ×3, fallback cũng 503`) — đã chạy trong `llm_retry_scenarios.py`.
</details>

## Self-check questions
1. Vì sao pytest dùng `assert` trần? Fixture được tiêm thế nào?
2. `tmp_path` và `monkeypatch` giải quyết gì?
3. Fake, stub, mock khác nhau ở đâu? Repo ưu tiên cái nào?
4. `FakeClock.sleep` làm gì và tại sao có ích?
5. `api_error` vì sao dựng đúng body của lỗi Google?
6. Test flaky duy nhất của repo là gì và nó được xử lý thế nào?
7. Đột biến "sống sót" có thể do những nguyên nhân nào?
8. Vì sao "chạy lại là xanh" là thói quen xấu?

## Interview Q&A
1. **"Bạn kiểm thử code gọi API bên ngoài thế nào?"** — Đặt sau interface, dùng fake có kịch bản thất bại, tiêm đồng hồ/sleep; mặc định offline, test live tách bằng marker ([REPO pyproject.toml:25-31]).
2. **"Coverage 100% có đủ không?"** — Không; chỉ nói dòng nào được chạy. Mutation testing kiểm test có **bắt lỗi**; repo dùng như cổng nghiệm thu ([REPO AI_WORKLOG.md:351-352]).
3. **"Bạn xử lý test flaky ra sao?"** — Thu bằng chứng có hệ thống (15/15), không che giấu, ghi nhận nguyên nhân nghi ngờ nhưng chưa xác nhận ([REPO README.md:305-309]).
4. **"Làm sao test độ trễ/retry mà không chờ thật?"** — Đồng hồ giả trong đó `sleep` cộng thời gian ([REPO tests/fakes.py:50-62]).
5. **"Bạn giữ kiến trúc phân tầng thế nào?"** — Một test dùng `ast` quét import và fail nếu vi phạm ([REPO CLAUDE.md:7]).
6. **"Một sai lầm bạn từng gặp khi thử đột biến?"** — Khôi phục bằng `git checkout` trên file chưa được theo dõi khiến đột biến ở lại; bắt được nhờ `grep` lại trước khi commit ([REPO AI_WORKLOG.md:129-131]).

## Further reading
- pytest docs (`https://docs.pytest.org`) — fixtures, parametrize, monkeypatch, `tmp_path`. `[GENERAL]`
- Martin Fowler, *Mocks Aren't Stubs* — phân biệt fake/stub/mock. `[GENERAL]`
- Mutation testing: tài liệu của `mutmut` (Python) hoặc bài tổng quan trên Wikipedia "Mutation testing". `[GENERAL]`
- Google Testing Blog: bài về **flaky tests**. `[GENERAL]`
- Tiếp theo: [15](15-ai-assisted-dev-workflow.md) (quy trình executor/verifier).
