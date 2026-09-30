# 04 · Dữ liệu vào/ra và các mẫu độ bền: JSONL, append-only, hash, cache, idempotent, resume, tính xác định
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [01](01-python-for-csharp-devs.md), [01b](01b-python-code-reading-guide.md), [03](03-architecture-and-gui.md), [06](06-embeddings-and-vector-search.md) · Study time: ~8–10h · Home file của: JSON Lines (JSONL), append-only + `fsync`, torn write, ghi nguyên tử (tmp + `os.replace`), `latest_records` (dòng cuối thắng), khoá cache dựa trên hash, cache SQLite (BLOB float32, một transaction mỗi lời gọi), idempotency (index theo `chunk_id`), resume có kiểm tra cấu hình (`run.json`), UTF-8/LF, tính xác định (determinism)
> Bài tập chạy được: `learning/_tools/exercises/persistence_scenarios.py` (offline; chỉ ghi vào thư mục tạm của hệ điều hành, không đụng repo, không mạng, không key).

## Vì sao file này quan trọng trong dự án
Dự án chạy những việc **đắt và dễ gián đoạn**: embed 1568 request trên hai ngày (file 06), chạy đánh giá ~122 lời gọi LLM, chấm judge 61 lần (file 11). Nếu tiến trình chết giữa chừng mà mất hết, bạn đốt quota vô ích (và quota là thứ khan hiếm). Vì vậy repo có một bộ mẫu thiết kế nhỏ, lặp đi lặp lại ở mọi nơi: **ghi từng dòng bền vững**, **khoá bằng hash**, **chạy lại thì chỉ làm phần còn thiếu**, và **từ chối tiếp tục nếu điều kiện đã đổi**. Các mẫu này áp dụng cho mọi hệ thống xử lý dữ liệu/ML thực tế, nên rất đáng học kỹ.

---

## Level 1 — Basic

### 1.1 JSON Lines (JSONL): mỗi dòng một đối tượng JSON
- **Ý tưởng:** một file JSON thường là **một** tài liệu lớn; muốn thêm một bản ghi phải ghi lại cả file. **JSONL** để **mỗi dòng là một JSON độc lập**, nên thêm bản ghi = nối thêm một dòng. Đọc theo từng dòng cho phép xử lý file lớn mà không nạp hết vào bộ nhớ.
- **Trong repo này:** dữ liệu chunk, bộ câu hỏi, kết quả chạy, judgement, log lập chỉ mục đều là JSONL (ví dụ `eval-v1.jsonl` 36 dòng, `records.jsonl`, `judgements.jsonl`). CLAUDE.md liệt kê "JSON/JSONL" trong stack khoá. [REPO CLAUDE.md:6]
- **Ghi JSONL — mã thật:** một dòng cho mỗi bản ghi, `ensure_ascii=False` (giữ nguyên tiếng Việt, không escape `\uXXXX`), UTF-8, và **ép** kết thúc dòng là `\n`:
**`src/knowledge_assistant/application/ingestion/normalize_corpus.py:75-79`**
```python
def write_jsonl(records: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8", newline="\n"
    )
```
- **Đọc chậm:** `"".join(json.dumps(record) + "\n" for record in records)` là biểu thức generator nối tất cả dòng thành một chuỗi; `newline="\n"` là tham số của `Path.write_text` để **không** đổi `\n` thành `\r\n` trên Windows.
- **C# analogy:** `File.AppendAllLines`/`StreamWriter` ghi mỗi dòng một `JsonSerializer.Serialize(obj)`; đọc bằng `File.ReadLines` + `Deserialize` (giống NDJSON).
- **Tại sao:** append-only rẻ và an toàn hơn sửa file lớn tại chỗ; và diff Git theo dòng có ý nghĩa.
- **Pitfalls `[REAL]`:** trên Windows, một test của INGEST-003 fail vì hàm helper dùng `Path.write_text` **không** có `newline="\n"` (ghi CRLF, trong khi đường HTML→Markdown cho LF). Sửa ở helper bằng `newline="\n"`. [REPO docs/reports/execution/INGEST-003.md:66]

### 1.2 Hash (SHA-256) làm "danh tính nội dung"
- **Ý tưởng:** hàm băm mật mã (SHA-256) biến bất kỳ chuỗi nào thành 64 ký tự hex; **cùng nội dung → cùng hash**, đổi một ký tự → hash khác hẳn. Dùng để (1) nhận diện nội dung (khoá cache), (2) phát hiện thay đổi (đóng băng file, file 10 §3.1), (3) khử trùng lặp (file 07).
- **Trong repo này:** ba chỗ khác nhau, cùng một hàm:
  - `content_hash` / `passage_hash` của chunk (file 07);
  - `sha256(model|task|text)` làm khoá cache embedding (2.4);
  - SHA-256 của file câu hỏi/prompt để kiểm tính toàn vẹn (file 10, 11).
  Snapshot corpus cũng lưu SHA-256 của từng file nguồn trước khi di chuyển, để chứng minh corpus **không bị sửa**. [REPO docs/snapshots/corpus/2026-09-24-initial.md:7]
- **C# analogy:** `SHA256.HashData(Encoding.UTF8.GetBytes(s))` → `Convert.ToHexString`. Python: `hashlib.sha256(s.encode("utf-8")).hexdigest()`.
- **Tại sao mã hoá thành bytes rõ ràng (`.encode("utf-8")`):** hash tính trên **bytes**, không phải chuỗi; nếu không nói rõ bảng mã, cùng chuỗi có thể cho hash khác nhau giữa môi trường.
- **Pitfalls `[GENERAL]`:** SHA-256 ở đây dùng làm **nhận dạng**, không phải bảo mật mật khẩu. Nếu hai file khác nhau về dấu xuống dòng (`\r\n` vs `\n`) thì hash khác — lý do dự án ép LF (3.3).

### 1.3 Idempotent, xác định (deterministic), append-only: ba từ khoá
- **Idempotent:** chạy một thao tác **hai lần** cho cùng kết quả như chạy một lần. Ví dụ: lập chỉ mục lần hai không nhúng lại chunk đã có (2.5).
- **Xác định (deterministic):** cùng đầu vào → cùng đầu ra. Ví dụ: `chunk_id = source:config:index:04d` — lặp lại quá trình chunk cho cùng id (file 07); cùng text → cùng vector giả trong `FakeEmbedder` (đã chạy thử, mục cuối C5: `FakeEmbedder().vector("x")` hai lần bằng nhau).
- **Append-only:** chỉ **thêm** dòng, không sửa/xoá dòng cũ. Lỗi cũ vẫn còn để truy vết; "trạng thái hiện tại" là **dòng cuối** của mỗi khoá (2.2).
- **Tại sao ba thứ này đi cùng nhau:** chúng làm cho một pipeline dài có thể **dừng và chạy tiếp** an toàn, và cho kết quả **kiểm chứng được**.
- **Pitfalls `[GENERAL]`:** nhầm "idempotent" với "xác định". Gọi API `POST /orders` hai lần không idempotent dù mỗi lần xác định; index theo `chunk_id` thì idempotent vì khoá là danh tính.

---

## Level 2 — Intermediate

### 2.1 Ghi bền vững: một dòng, `flush` + `fsync`, và "torn write"
- **Ý tưởng:** nếu tiến trình chết **giữa lúc ghi**, file có thể chứa một dòng **cụt** (torn write). Quy ước của `JsonlRecordStore`: mỗi lần ghi là **một dòng kết thúc bằng `\n`**, `flush` rồi `fsync` (buộc hệ điều hành đẩy xuống đĩa) **trước khi** lời gọi trả về — tối đa mất **dòng đang ghi**. Chỉ dòng có `\n` mới tính là bản ghi.
**`src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:1-9`**
```python
"""RecordStore on disk: `run.json`, `records.jsonl` and `errors.jsonl` in one run directory (EVAL-003a), plus the
judge's `judgements.jsonl` (JudgementStore, EVAL-003b).

Every write is one newline-terminated line, flushed and fsynced before the call returns, so a killed process loses at
most the line being written. Only newline-terminated lines are records: an unterminated tail is a torn write, ignored by
`read_records` and cut off by the next append (the case is then simply run again). A complete line that is not JSON is
corruption and raises. Every line passes `redact` first, so an API key can never reach a results file. Files are UTF-8
with "\n" line ends, whatever the platform.
"""
```
**`src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:71-82`**
```python
    def _append(self, name: str, item: dict) -> None:
        line = self._redact(json.dumps(item, ensure_ascii=False, allow_nan=False)) + "\n"  # raises before any write
        self._dir.mkdir(parents=True, exist_ok=True)
        with (self._dir / name).open("ab+") as handle:
            if handle.seek(0, os.SEEK_END):  # a non-empty file must end with a newline
                handle.seek(-1, os.SEEK_END)
                if handle.read(1) != b"\n":
                    handle.seek(0)
                    handle.truncate(handle.read().rfind(b"\n") + 1)  # everything after the last newline is torn
            handle.write(line.encode("utf-8"))  # append mode: always at the end
            handle.flush()
            os.fsync(handle.fileno())
```
- **Đọc chậm (phần khó):**
  - `line = redact(json.dumps(item, ..., allow_nan=False)) + "\n"` được tính **trước** khi mở file: nếu `json.dumps` ném lỗi (ví dụ `NaN`), **không** có byte nào bị ghi ("raises before any write").
  - `open("ab+")` = mở **nhị phân, thêm cuối, cho phép đọc**; `handle.seek(0, os.SEEK_END)` trả về kích thước (khác 0 nếu file không rỗng).
  - Nếu byte cuối **không** là `\n` → có đuôi cụt: `handle.seek(0)`; `handle.truncate(handle.read().rfind(b"\n") + 1)` **cắt** mọi thứ sau dấu xuống dòng cuối, rồi mới ghi dòng mới.
  - `handle.write(...)` rồi `flush()` + `os.fsync(handle.fileno())`.
- **Đã chạy thử offline** (`persistence_scenarios.py`): mục P1 ghi 2 bản ghi (2 dấu `\n`), secret `SECRETKEY` được thay bằng `[redacted]` **trước khi** xuống đĩa; mục P2 thêm một dòng cụt `{"case_id": "c2", "arm": "A", "mo`: `read_records` **bỏ qua** (vẫn 2 bản ghi) rồi lần `append_record` kế tiếp **cắt** đuôi cụt và ghi bản ghi mới (3 bản ghi, 3 dòng); mục P4 ghi `NaN` → `ValueError` và file **không đổi**.
- **C# analogy:** `FileStream` với `FileOptions.WriteThrough` + `Flush(true)`; hoặc `File.AppendAllText` bọc trong một bước "kiểm tra dòng cụt". Cùng ý tưởng với **write-ahead log** của cơ sở dữ liệu.
- **Tại sao `redact` trước khi ghi:** không bao giờ để API key lọt vào file kết quả (CLAUDE.md rule 7). [REPO CLAUDE.md:11]
- **Pitfalls `[GENERAL]`:** `flush()` chỉ đẩy buffer của Python xuống hệ điều hành; **`fsync`** mới đẩy xuống đĩa. Bỏ `fsync` thì mất điện có thể mất các dòng đã "ghi xong". Đổi lại `fsync` chậm — ở đây chấp nhận vì mỗi record là một lời gọi API đắt.

### 2.2 Đọc lại: bỏ đuôi cụt, báo lỗi khi hỏng thật, "dòng cuối thắng"
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
- **Đọc chậm:** `*complete, _torn_tail = path.read_bytes().split(b"\n")` là **star-unpacking**: mọi mảnh trừ mảnh cuối vào `complete`, mảnh cuối (sau `\n` cuối cùng — rỗng nếu file kết thúc đúng) vào `_torn_tail` và bị **bỏ qua**. `except ValueError` bắt cả `JSONDecodeError` lẫn `UnicodeDecodeError` (cả hai là lớp con của `ValueError`).
- **Hai loại "dòng xấu" được xử lý khác nhau:** đuôi **không có `\n`** = ghi dở → bỏ qua (case sẽ chạy lại); dòng **đủ `\n` nhưng không phải JSON** = **hỏng thật** → ném `EvaluationError` có số dòng. Đã chạy thử (mục P3): thêm dòng `not json\n` → `EvaluationError: ... Expecting value: line 1 column 1`.
- **"Dòng cuối thắng":** file chỉ thêm, nên một case thử lại để lại **cả dòng lỗi cũ lẫn dòng mới**. Hàm `latest_records` chọn bản ghi cuối theo khoá `(case_id, arm, mode)`:
**`src/knowledge_assistant/application/evaluation/records.py:111-116`**
```python
def latest_records(records: list[dict]) -> dict[RecordKey, dict]:
    """The last line per (case_id, arm, mode), in first-seen order: what a retry left is the case's final state."""
    latest: dict[RecordKey, dict] = {}
    for record in records:
        latest[record_key(record)] = record
    return latest
```
  Đã chạy thử (mục P1): ghi một `error` rồi một `ok` cho cùng khoá → `read_records` trả `['error','ok']`, `latest_records` trả `{('c1','A','full'): 'ok'}`.
- **C# analogy:** giống một **event log** + "trạng thái hiện tại = fold các sự kiện" (event sourcing nhẹ); hoặc `GroupBy(key).Select(g => g.Last())`.
- **Tại sao không sửa dòng cũ:** giữ lịch sử để truy vết (bao nhiêu lần thử, lỗi gì), và tránh ghi đè làm mất dữ liệu. [REPO src/knowledge_assistant/application/evaluation/records.py:10]
- **Pitfalls `[GENERAL]`:** ai đọc file JSONL thô (không qua `latest_records`) sẽ đếm trùng. Ghi rõ quy ước này ở nơi định nghĩa — repo đã ghi trong docstring `RecordStore`. [REPO src/knowledge_assistant/core/interfaces/record_store.py:4-18]

### 2.3 Ghi nguyên tử một file nhỏ (manifest): tmp + `os.replace`
- **Vấn đề:** `run.json` (manifest) là một JSON **đầy đủ**, không thể "nối dòng". Nếu chết giữa lúc ghi, người đọc thấy file nửa vời.
- **Giải pháp:** ghi ra `run.json.tmp` (kèm `flush` + `fsync`), rồi **`os.replace`** đổi tên sang `run.json` — đổi tên trong cùng một ổ đĩa là **nguyên tử**: người đọc thấy bản cũ hoặc bản mới, **không bao giờ** một nửa.
**`src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:32-40`**
```python
    def write_manifest(self, manifest: dict) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        text = self._redact(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)) + "\n"
        temporary = self._dir / f"{MANIFEST}.tmp"
        with temporary.open("wb") as handle:
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self._dir / MANIFEST)  # atomic: a reader sees the old or the new manifest, never half
```
- **Đã chạy thử offline** (mục P5): ghi manifest hai lần → đọc lại `{'run_id': 'r1', 'config': {'a': 2}}` và thư mục chỉ còn `run.json` (không còn `.tmp`).
- **C# analogy:** `File.Replace(src, dest, backup)` hoặc mẫu "ghi ra temp rồi `File.Move(overwrite: true)`".
- **Tại sao:** mọi nơi cần **cập nhật cả một file** một cách an toàn nên dùng mẫu này.
- **Pitfalls `[GENERAL]`:** `os.replace` chỉ nguyên tử khi hai đường dẫn cùng **ổ/hệ thống file**; vì vậy file tạm được tạo cùng thư mục với đích.

### 2.4 Cache embedding: khoá là hash, giá trị là BLOB float32
- **Home:** cơ chế embed/batch/quota của `CachingEmbedder` được dạy đầy đủ ở [06 §2.5](06-embeddings-and-vector-search.md), còn mẫu Decorator ở [03 §2.2](03-architecture-and-gui.md). **Ở đây chỉ nhấn mạnh phần độ bền dữ liệu** (khoá theo hash, BLOB float32, commit theo từng lời gọi) — đọc hai file kia trước nếu chưa quen.
- **Ý tưởng:** nhúng một câu tốn quota (file 06). Bọc bất kỳ `Embedder` nào bằng `CachingEmbedder` (mẫu **Decorator**, file 03): tra cache trước, chỉ các **miss** đi tới embedder thật.
- **Khoá và định dạng lưu:**
**`src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:32-41`**
```python
def cache_key(model_id: str, task: EmbeddingTask, text: str) -> str:
    return hashlib.sha256(f"{model_id}|{task.value}|{text}".encode("utf-8")).hexdigest()


def _to_blob(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _from_blob(blob: bytes, dim: int) -> list[float]:
    return list(struct.unpack(f"<{dim}f", blob))
```
  - Khoá = `sha256("model|task|text")`. **Vì sao gồm model và task?** Cùng một câu nhưng khác model (hoặc khác *task* `DOCUMENT` vs `QUERY`) cho **vector khác**; nếu không đưa vào khoá, bạn sẽ dùng nhầm vector.
  - Vector lưu bằng `struct.pack("<768f", ...)`: 768 số **float32** little-endian = 3072 byte, thay vì JSON (dài hơn nhiều).
- **Đã chạy thử offline** (mục C1–C2): khoá dài 64 hex; thay **task** → khoá khác; thay **model** → khác; thêm một khoảng trắng vào text → khác; vector `[0.1, -0.5, 1/3]` sau vòng `_to_blob`/`_from_blob` thành `[0.10000000149011612, -0.5, 0.3333333432674408]` (12 byte): **mất một chút độ chính xác** (float64 → float32) — chấp nhận được với embedding.
- **Đọc chậm:** `f"<{len(vector)}f"` là **chuỗi định dạng** cho `struct`: `<` little-endian, số lượng, `f` = float32.
- **C# analogy:** `MemoryMarshal.AsBytes(float[])`/`BinaryWriter.Write(float)` hoặc `Buffer.BlockCopy`; khoá tương ứng `$"{model}|{task}|{text}"` băm bằng SHA-256.
- **Tại sao lưu cùng giá trị float32 cho cả "lần đầu" và "lần sau":** trong `_embed_and_store`, dòng `stored[key] = _from_blob(blob, len(vector))` trả về vector **đã qua float32**, để kết quả lần đầu và lần cache-hit **giống hệt nhau** — tính xác định. [REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:159]

### 2.5 Không mất tiền đã trả: một transaction mỗi lời gọi nhà cung cấp
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
**`src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:144-162`**
```python
    def _embed_and_store(self, batch: list[tuple[str, str]], task: EmbeddingTask) -> dict[str, list[float]]:
        texts = [text for _, text in batch]
        vectors = self._inner.embed(texts, task)
        self.inner_calls += 1
        if len(vectors) != len(texts):
            raise EmbeddingError(f"inner embedder returned {len(vectors)} vectors for {len(texts)} texts")
        self.misses += len(texts)
        self.estimated_tokens += sum(estimate_tokens(t) for t in texts)

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        stored: dict[str, list[float]] = {}
        rows = []
        for (key, _), vector in zip(batch, vectors):
            blob = _to_blob(vector)
            rows.append((key, self.model_id, task.value, len(vector), blob, now))
            stored[key] = _from_blob(blob, len(vector))  # same float32 values as a later cache hit
        with self._db:  # one transaction per provider call
            self._db.executemany("INSERT OR REPLACE INTO embeddings VALUES (?, ?, ?, ?, ?, ?)", rows)
        return stored
```
- **Đọc chậm:**
  - `dict.fromkeys(keys)` khử trùng lặp giữ thứ tự (file 01b); `missing: dict[str, str]` gom **mỗi text cần nhúng đúng một lần** (`a` xuất hiện hai lần chỉ gửi một).
  - `self._inner.plan_calls(...)` là **quyền của embedder bên trong** quyết định cách chia lô (số text và token tối đa mỗi lời gọi; file 06); cache **không tự cắt lại** ("the cache never re-slices"), nên một nhóm = **đúng một lời gọi trả tiền**.
  - `with self._db:` là **context manager** của `sqlite3`: **một transaction** — `commit` khi khối kết thúc thành công, `rollback` nếu có ngoại lệ. `INSERT OR REPLACE` làm cho lưu lại cùng khoá là an toàn.
  - Hai kiểm tra `if [text ...] != list(group): raise EmbeddingError(...)` và `if start != len(pending)` bảo vệ **hợp đồng** của `plan_calls`.
- **Đã chạy thử offline** (mục C3): với `FakeEmbedder(batch_size=2)`, embed `["a","b","a","c","d"]` → 5 vector trả về nhưng chỉ **4 miss** (trùng `a` gửi một lần) trong **2 lời gọi** `[2, 2]`; chạy lại y hệt → `hits = 4`, **không thêm lời gọi**; cùng text `a` nhưng `task=QUERY` → **miss** (khoá khác).
- **Đã chạy thử offline** (mục C4 — quan trọng nhất): embedder giả **ném lỗi ở lời gọi thứ hai** (mô phỏng hết quota). Sau lỗi, `misses = 2`: kết quả của lời gọi thứ nhất **đã được commit**. Chạy lại: `2 hits, 3 misses`; các lần gọi mới chỉ gồm `[['t3','t4'], ['t5']]` — **không gửi lại** `t1`,`t2`. Đúng tinh thần docstring: "A crash or quota stop therefore never loses a paid call's vectors". [REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:1-6]
- **Đã chạy thử offline** (mục C5): `plan_calls` sai (bỏ sót text) → `EmbeddingError: inner plan_calls covered 1 of 2 texts`.
- **Tại sao đây là mẫu đáng chép:** trong pipeline đắt tiền, **đơn vị commit phải bằng đơn vị chi phí**. Nếu commit cuối cùng một lần thì lỗi ở lời gọi 700/709 làm mất 699 lời gọi đã trả.
- **Pitfalls `[GENERAL]`:** SQLite connection có **thread affinity** (file 03 §`PerCallEmbedder`): mỗi luồng cần connection riêng. Và `IN (?, ?, ...)` bị giới hạn số tham số nên `LOOKUP_CHUNK = 500` chia nhỏ tra cứu (dòng 29).

### 2.6 Lập chỉ mục idempotent: khoá là `chunk_id`
- **Ý tưởng:** trước khi nhúng, hỏi vector store "id nào đã có?", chỉ xử lý phần **chưa có** (`pending`). Lập chỉ mục lần hai (khi không có gì mới) không gọi API và không đổi kết quả.
**`src/knowledge_assistant/application/ingestion/index_corpus.py:71-77`**
```python
    def pending(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Chunks whose chunk_id is not in the store yet, in file order."""
        ids = [chunk.chunk_id for chunk in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("chunk file has duplicate chunk_ids")
        present = self._store.get_ids()
        return [chunk for chunk in chunks if chunk.chunk_id not in present]
```
**`src/knowledge_assistant/application/ingestion/index_corpus.py:84-92`**
```python
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
- **Đọc chậm:** `set(ids)` so với `len(ids)` để phát hiện `chunk_id` trùng (vi phạm khoá danh tính) — ném `ValueError` thay vì lặng lẽ ghi đè; `todo` rỗng thì không gọi `embed` (nhánh `if todo:`); `upsert` theo lô `upsert_batch=100`. Báo cáo `IndexReport` ghi `already_present` (số bị bỏ qua = resume) và `newly_embedded`.
- **Tại sao:** `chunk_id = source:config:index:04d` **xác định** (file 07), nên cùng chunker + cùng corpus → cùng id → chạy lại là **no-op**. Tính xác định của id là điều kiện của idempotency.
- **C# analogy:** `INSERT ... ON CONFLICT DO NOTHING`/`upsert` theo khoá tự nhiên; `HashSet.Contains` trước khi thêm.
- **Pitfalls `[GENERAL]`:** idempotency chỉ đúng nếu **khoá thực sự xác định nội dung**. Nếu bạn đổi nội dung chunk mà giữ `chunk_id`, lần chạy lại **không** cập nhật (vì id đã có). Repo tránh bằng cách cho `chunk_id` chứa cấu hình chunker và giữ tập chunk đóng băng sau khi build.

---

## Level 3 — Advanced

### 3.1 Resume có kiểm tra cấu hình: "một lần chạy không bao giờ trộn thiết lập"
- **Ý tưởng:** runner đánh giá ghi `run.json` (manifest) chứa **toàn bộ thiết lập quyết định ý nghĩa của kết quả** (model, prompt, ngưỡng, split...). Khi chạy tiếp (`resume`), nó **so** thiết lập hiện tại với thiết lập đã ghi; **khác → từ chối** và bảo "start a new run instead":
**`src/knowledge_assistant/application/evaluation/run_evaluation.py:433-444`**
```python
    def _check_resumable(self, manifest: dict | None) -> None:
        """A recorded run continues only with the settings it started with (git state and times are not settings)."""
        if manifest is None:
            return
        config, recorded = self._config.to_dict(), manifest["config"]
        differing = sorted(key for key in config.keys() | recorded.keys() if config.get(key) != recorded.get(key))
        if manifest.get("run_id") != self._run_id or differing:
            raise RunConfigMismatch(
                f"run {self._run_id} was started with different settings, so it cannot be resumed: "
                + "; ".join(f"{key}: recorded {recorded.get(key)!r}, now {config.get(key)!r}" for key in differing)
                + " (start a new run instead)"
            )
```
- **Đọc chậm:** `config.keys() | recorded.keys()` là **hợp** hai tập khoá (toán tử `|` trên `dict_keys`); `differing` gồm mọi khoá khác nhau (kể cả khoá chỉ có một bên); thông báo lỗi liệt kê `recorded ...` vs `now ...` bằng `!r` (repr) để thấy rõ giá trị. Git commit, cờ dirty và thời gian **không** phải thiết lập (mỗi lần gọi ghi riêng). [REPO src/knowledge_assistant/application/evaluation/run_evaluation.py:6-7]
- **Một chi tiết hay:** manifest được **ghi trước** khi chạy ("written first: a killed process still leaves its invocation behind"), nên một tiến trình bị kill vẫn để lại dấu vết lần gọi. [REPO src/knowledge_assistant/application/evaluation/run_evaluation.py:430]
- **Quy tắc resume:** case có bản ghi cuối `ok` thì bỏ qua; case `error` thì chạy lại (dòng lỗi cũ vẫn ở đó). [REPO src/knowledge_assistant/application/evaluation/run_evaluation.py:5]
- **C# analogy:** giống việc từ chối áp dụng một migration nếu checksum của migration đã áp dụng khác (Flyway/EF Migrations kiểm checksum).
- **Tại sao:** kết quả A/B chỉ có nghĩa khi **cùng thiết lập**. Nếu ai đó đổi prompt giữa hai lần resume, bảng kết quả trộn hai prompt mà không ai biết. Máy từ chối = không thể quên.
- **Pitfalls `[GENERAL]`:** kiểm "cấu hình" chỉ bảo vệ những thứ bạn đưa vào manifest; nếu thiếu một thiết lập (ví dụ phiên bản thư viện), sự khác biệt bị bỏ sót. Vì vậy manifest ghi `git_commit` và `git_dirty` như bằng chứng bổ sung.

### 3.2 Đường dữ liệu qua các tầng: ai sở hữu định dạng nào
- **Tầng core** chỉ biết **giao diện** (`RecordStore`, `JudgementStore`, `Embedder`) — không biết JSONL hay SQLite. **Tầng infrastructure** cài đặt bằng file JSONL, SQLite, Chroma. Nhờ vậy `RunEvaluation` (application) test được với store giả trong bộ nhớ. [REPO src/knowledge_assistant/core/interfaces/record_store.py:4-29]
- **Tại sao chọn định dạng nào cho việc gì (`[GENERAL]` suy luận từ repo):**
  | Dữ liệu | Định dạng | Vì sao hợp lý |
  |---|---|---|
  | kết quả từng case, judgement, log | JSONL append-only | ghi từng dòng, thêm chứng cứ, đọc bằng mắt/`diff` |
  | manifest một lần chạy | JSON + ghi nguyên tử | cần đọc-ghi cả file, ít khi đổi |
  | embedding | SQLite BLOB | tra cứu theo khoá nhanh, transaction, nhiều triệu byte |
  | vector tìm kiếm | ChromaDB | ANN/HNSW (file 06) |
- **C# analogy:** chọn giữa `appsettings.json`, EF Core + SQLite, và Elasticsearch — mỗi thứ cho một loại truy cập.
- **Pitfalls:** đừng dùng SQLite làm log audit **chỉ thêm** nếu cần `diff` bằng mắt; đừng dùng JSONL làm kho truy vấn theo khoá lớn.

### 3.3 Nhất quán byte: UTF-8, `LF` và hash
- **Vấn đề:** cùng một chuỗi nhưng khác dấu xuống dòng (`\r\n` Windows vs `\n`) → **hash khác**, diff Git ầm ĩ. Repo quyết: mọi file văn bản lưu và checkout bằng **LF** trên mọi hệ điều hành: `.gitattributes` có `* text=auto eol=lf`. [REPO .gitattributes:1-3]
- **Trong code:** mọi ghi JSONL dùng `encoding="utf-8"` và `newline="\n"`; docstring của store ghi rõ "Files are UTF-8 with \n line ends, whatever the platform." [REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:7-8]
- **Sự cố `[REAL]`:** lịch sử git có commit `07264fc` với tiêu đề "EVAL-004a: report the committed (LF) summary.json hashes" (đọc bằng `git show`): báo cáo phải ghi hash của bản **đã commit (LF)**, không phải bản trên máy; cộng với test Windows ở 1.1. Hai sự cố cùng một gốc: **dấu xuống dòng thay đổi byte**. (Chi tiết diff của commit tôi không đọc từng dòng.)
- **Ngoại lệ có chủ ý:** `MarkdownParser` **giữ nguyên** dấu xuống dòng của tài liệu nguồn "by design" (ADR-0003 D1); chuẩn hoá xảy ra **trong bộ nhớ** ở tầng normalize, không sửa corpus (CLAUDE.md rule 4). [REPO CLAUDE.md:8]
- **Tại sao quan trọng:** hash/đóng băng/cache đều dựa trên **bytes**. Nếu nền tảng đổi bytes thầm lặng, mọi bảo đảm hỏng mà không có lỗi rõ ràng.
- **Pitfalls `[GENERAL]`:** trên Windows `open(path, "w")` (chế độ text) đổi `\n` thành `\r\n`; luôn chỉ định `newline=""`/`"\n"` với dữ liệu cần byte chính xác.

### 3.4 Tính xác định: nguồn và giới hạn
- **Nguồn xác định trong repo:** `chunk_id` từ (nguồn, cấu hình, chỉ số); khoá cache từ hash; seed cố định cho bootstrap (file 12); `temperature=0` cho LLM (file 08); FakeEmbedder băm `(task, text)`.
- **Nguồn KHÔNG xác định (được ghi nhận):**
  - Thứ tự/giá trị từ **HNSW** trong Chroma: có test không ổn định ở `test_chroma_store.py` (lỗi compaction "flaky", file 06).
  - Đầu ra LLM: temperature 0 vẫn không bảo đảm giống hệt (file 08 §3.2).
  - Thời gian/độ trễ: phụ thuộc mạng và cache (file 13).
- **Bài học:** **cô lập** phần không xác định (ở biên, có ghi nhận) và giữ phần còn lại xác định để kiểm thử được offline.
- **Pitfalls `[GENERAL]`:** "đã seed rồi" ≠ "xác định": thư viện đa luồng, thứ tự duyệt dict/set (`set` không giữ thứ tự chèn!) và số float có thể phá xác định. Repo dùng `dict.fromkeys` (giữ thứ tự) thay `set` khi cần thứ tự.

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Vì sao dữ liệu kết quả dùng JSONL chứ không phải một file JSON mảng?
<details><summary>Đáp án</summary>
JSONL cho phép **thêm** một bản ghi bằng cách nối một dòng (không phải ghi lại cả file), đọc/ghi từng dòng, chịu được ghi dở (chỉ mất dòng cuối), và `diff` theo dòng. Một file JSON mảng phải parse/ghi lại toàn bộ và một lần ghi hỏng làm hỏng cả file ([REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:1-9]).
</details>

**B2 (Basic).** Hai lần chạy `cache_key("m@8", DOCUMENT, "hello")` và `cache_key("m@8", QUERY, "hello")` có bằng nhau không? Vì sao?
<details><summary>Đáp án</summary>
Không (mục C1: `False`). Khoá chứa `task`; embedding tài liệu và câu hỏi dùng chế độ khác nhau nên vector khác — dùng chung một entry sẽ sai ([REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:32-33]).
</details>

**B3 (Basic).** `latest_records` trên `[error(c1), ok(c1), ok(c2)]` trả gì?
<details><summary>Đáp án</summary>
`{("c1", arm, mode): ok, ("c2", arm, mode): ok}` theo thứ tự thấy đầu tiên; bản ghi `ok` của `c1` **thay** bản `error` ([REPO src/knowledge_assistant/application/evaluation/records.py:111-116]; kiểm ở mục P1).
</details>

**I1 (Intermediate).** Tiến trình chết khi đang ghi một dòng và để lại đuôi `{"case_id": "c2", "arm": "A", "mo`. Chuyện gì xảy ra ở (a) `read_records`, (b) `append_record` tiếp theo?
<details><summary>Đáp án</summary>
(a) Mảnh sau `\n` cuối cùng bị coi là đuôi cụt và **bỏ qua** (vẫn đọc được các bản ghi đầy đủ). (b) `_append` thấy byte cuối không phải `\n`, **cắt** phần sau `\n` cuối rồi ghi dòng mới; case dở dang được chạy lại. Đã chạy: sau đuôi cụt vẫn 2 bản ghi, sau append là 3 bản ghi và 3 dấu `\n` (mục P2).
</details>

**I2 (Intermediate).** Một embedder ném lỗi ở lời gọi thứ hai trong ba lời gọi dự kiến. Có bao nhiêu vector được lưu? Chạy lại gửi gì?
<details><summary>Đáp án</summary>
Chỉ vector của lời gọi thứ nhất được commit (mỗi nhóm một transaction). Chạy lại: các text của lời gọi 1 là cache-hit, chỉ gửi phần chưa có — đúng số liệu mục C4: `misses = 2` sau lỗi; lần sau `2 hits, 3 misses`, gửi `[t3,t4]`, `[t5]` ([REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:98-120]).
</details>

**I3 (Intermediate).** Vì sao `json.dumps(..., allow_nan=False)` được dùng, và điều gì xảy ra khi bản ghi có `float("nan")`?
<details><summary>Đáp án</summary>
`NaN` không phải JSON hợp lệ (nhiều bộ đọc khác từ chối). Với `allow_nan=False`, `json.dumps` ném `ValueError` **trước khi** mở file, nên không byte nào được ghi (mục P4: `ValueError: Out of range float values are not JSON compliant` và file không đổi) ([REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:72]).
</details>

**A1 (Advanced).** Vì sao manifest dùng tmp + `os.replace` còn records dùng append + `fsync`? Có thể đổi chỗ không?
<details><summary>Đáp án</summary>
Records là **chuỗi sự kiện**, mỗi lần chỉ thêm một dòng — append + `fsync` làm hỏng tối đa dòng đang ghi và đuôi cụt được nhận diện. Manifest là **một tài liệu duy nhất** được **thay thế**; nếu chết giữa lúc ghi thì cả file hỏng, nên cần ghi nguyên tử. Đổi chỗ sẽ sai: append vào manifest làm file không còn là JSON hợp lệ; ghi nguyên tử từng record thì đắt và mất thứ tự lịch sử ([REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:32-40], [REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:71-82]).
</details>

**A2 (Advanced).** Ai đó đổi prompt trả lời từ `answer_v2` sang `answer_v3` rồi chạy `resume` cho một run cũ. Điều gì xảy ra và vì sao đó là hành vi đúng?
<details><summary>Đáp án</summary>
`_check_resumable` thấy `prompt_version` trong `config` khác giá trị đã ghi (config còn chứa `prompt_sha256`: "an edited prompt under the same version name is a different run", [REPO src/knowledge_assistant/application/evaluation/run_evaluation.py:67]) → ném `RunConfigMismatch` liệt kê `recorded 'answer_v2', now 'answer_v3'` và bảo "start a new run instead". Đúng vì các bản ghi cũ và mới sẽ dùng hai prompt khác nhau trong **cùng một** run → kết quả không so sánh được ([REPO src/knowledge_assistant/application/evaluation/run_evaluation.py:433-444]).
</details>

**A3 (Advanced).** Thiết kế một test (giấy) chứng minh "mất điện giữa lúc ghi record không làm hỏng file". Cần làm giả thao tác gì và khẳng định gì?
<details><summary>Đáp án</summary>
Ghi vài record hợp lệ; **ghi thêm byte dở** (không có `\n`) để giả lập crash; khẳng định `read_records()` trả đúng các record hợp lệ (không lỗi), rồi `append_record` một record mới và khẳng định file kết thúc bằng `\n`, chứa các record cũ + mới và **không** còn mảnh cụt. Đúng chính xác kịch bản P2 (chạy được) ([REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:4-6]).
</details>

## Self-check questions
1. JSONL khác JSON thường ở đâu, và vì sao phù hợp cho log?
2. `flush` khác `fsync` thế nào?
3. Torn write là gì? Code xử lý nó ở đâu?
4. Vì sao khoá cache gồm model và task?
5. Vì sao commit cache theo từng lời gọi nhà cung cấp?
6. "Idempotent" khác "xác định" ở đâu? Cho một ví dụ trong repo.
7. `_check_resumable` bảo vệ điều gì? Cái gì **không** được coi là thiết lập?
8. Vì sao ép `LF`?

## Interview Q&A
1. **"Bạn thiết kế pipeline dài có thể dừng và chạy tiếp thế nào?"** — Ghi từng dòng bền vững, khoá bằng hash/`chunk_id`, chỉ xử lý phần còn thiếu, manifest cấu hình và từ chối resume khi thiết lập đổi ([REPO src/knowledge_assistant/application/evaluation/run_evaluation.py:1-13]).
2. **"Làm sao ghi file an toàn khi mất điện?"** — Append từng dòng + `fsync` (chịu được dòng cụt); file nhỏ ghi nguyên tử bằng tmp + `os.replace` ([REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:32-40]).
3. **"Cache khoá theo gì?"** — Hash của (model, task, text) để tránh dùng nhầm vector; lưu float32 BLOB; commit theo từng lời gọi để không mất tiền đã trả ([REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:1-6]).
4. **"Idempotency là gì và làm sao đạt được?"** — Chạy nhiều lần = chạy một lần; đạt bằng khoá danh tính xác định (`chunk_id`) và kiểm "đã có chưa" trước khi làm ([REPO src/knowledge_assistant/application/ingestion/index_corpus.py:71-77]).
5. **"Kể một lỗi thật về xuống dòng."** — Test Windows fail vì `write_text` không có `newline="\n"`; và hash phải tính lại theo LF; dự án ép LF bằng `.gitattributes` ([REPO docs/reports/execution/INGEST-003.md:66], [REPO .gitattributes:1-3]).
6. **"Nguồn không xác định trong hệ thống của bạn là gì?"** — HNSW (test flaky), đầu ra LLM dù temperature 0, độ trễ; được cô lập ở biên và ghi nhận ([REPO docs/specs/generation-spec.md:30-32]).

## Further reading
- Python docs: `hashlib`, `sqlite3`, `struct`, `os.replace`, `pathlib.Path.write_text` (`https://docs.python.org/3/library/hashlib.html`). `[GENERAL]`
- JSON Lines (`https://jsonlines.org`) — đặc tả tối giản của định dạng. `[GENERAL]`
- SQLite docs, "Atomic Commit In SQLite" — nền tảng của transaction bền vững. `[GENERAL]`
- Kleppmann, *Designing Data-Intensive Applications* — chương về log và idempotency. `[GENERAL]`
- Tiếp theo: [14](14-testing-and-quality.md) (kiểm thử các mẫu này bằng fake) và [15](15-ai-assisted-dev-workflow.md).
