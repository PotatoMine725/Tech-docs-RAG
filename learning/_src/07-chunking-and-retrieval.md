# 07 · Chunking (Arm A vs Arm B), khử trùng, over-fetch và refusal gate
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [01](01-python-for-csharp-devs.md), [05](05-rag-fundamentals.md), [06](06-embeddings-and-vector-search.md) · Study time: ~9–11h · Home file của: chunking (fixed-size & header-aware), overlap, `display_text`/`embed_text`, hash nội dung, khử trùng, over-fetch, top-k, ngưỡng refusal gate
> Kết quả so sánh A vs B (thống kê) ở [13](13-case-study-exp-001.md); cách đo "hit" ở file 10.

## Vì sao file này quan trọng trong dự án
Câu hỏi khoa học chính của dự án là: **cắt tài liệu theo heading (Arm A) có tốt hơn cắt cửa sổ cố định (Arm B) không?** (ADR-0003 D7). Chunking quyết định "đơn vị được tìm thấy và được trích dẫn". Retrieval (top-k, khử trùng, gate) quyết định LLM được đọc **những gì**. Hai thứ này ảnh hưởng đến độ đúng của câu trả lời nhiều hơn prompt.

---

## Level 1 — Basic

### 1.1 Chunking là gì và vì sao phải cắt
- **Ý tưởng:** không thể nhét cả tài liệu vào prompt/embedding (giới hạn token, loãng nghĩa). Ta cắt tài liệu thành các **chunk** ~vài trăm token; mỗi chunk được embed và tìm riêng. Chunk quá lớn → loãng, tìm kém chính xác; quá nhỏ → mất ngữ cảnh.
- **Tham số của dự án** (ADR-0003 D3): tối đa **1 600 ký tự** (~400 token), tối thiểu 400; overlap **200** ký tự giữa các mảnh của cùng một section bị cắt. Đơn vị là **ký tự** (không phụ thuộc model embedding). [REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:23-25]
- **Cấu hình nằm trong file, không nằm trong code:**
@@SNIP config/chunking.json 3-21@@
  Khoá của mỗi arm (`header-1600`, `fixed-1600`) chính là `chunker_config` xuất hiện trong chunk ID.
- **C# analogy:** như `appsettings.json` chứa tham số; ở đây `factory.load_arm` đọc rồi dựng đúng chunker:
@@SNIP src/knowledge_assistant/infrastructure/chunking/factory.py 9-19@@
  `settings.pop("type")` lấy và **xoá** khoá `type`; `HeaderAwareConfig(**settings)` "bung" dict thành tham số theo tên (xem 01 §2.4).
- **Tại sao:** "Changing a value needs a new ADR or an amendment with evidence" (`_comment` trong file). Số liệu thí nghiệm không được đổi lặng lẽ.
- **Pitfalls:** `[GENERAL]` không có kích thước chunk "đúng" chung; nó phụ thuộc corpus. ADR-0003 dựa trên **phân phối đo được** của corpus (p25 ≈ 330, median ≈ 990, p75 ≈ 2 400 ký tự cho section H1–H3), không dựa trên kết quả retrieval. [REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:10]

### 1.2 Arm B — cửa sổ cố định (đơn giản nhất, đọc trước)
- **Ý tưởng:** cắt văn bản thành các cửa sổ `size_chars` ký tự, mỗi cửa sổ lùi `size − overlap` so với cửa sổ trước; không quan tâm cấu trúc.
- **Trong repo này:**
@@SNIP src/knowledge_assistant/infrastructure/chunking/fixed_size.py 36-49@@
  Đọc: `step = size − overlap`; vòng `while` tạo cửa sổ `[window, window+size)`; `trim` cắt khoảng trắng ở hai đầu; `section_path_at(document, start)` gán **heading gần nhất trước vị trí bắt đầu** (D5); `if end == len(text): break` dừng ở cửa sổ cuối.
- **Đã chạy thử offline:** văn bản 48 ký tự (`"".join(f"w{i:02d} " for i in range(12))`), `size=20, overlap=5` (step 15) → các span `(0,19)`, `(16,35)`, `(30,47)`: `trim` cắt khoảng trắng đầu/cuối nên số không tròn 20.
- **Tại sao:** đây là baseline "ngây thơ" để so với chunking theo cấu trúc.
- **Pitfalls `[REAL]`:** cắt cố định **chém ngang code block**. Số đo thật của corpus: **387/859 chunk (45.05%) của Arm B cắt qua một khối code**, so với **24/733 (3.27%)** của Arm A. [REPO docs/reports/execution/INGEST-004.md:45-50] Đây chính là failure mode ADR dự đoán ("fixed-size chunks separating code from its explanation"). [REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:63-69]

### 1.3 Cái gì được lưu trong một chunk
- **Ý tưởng:** chunker chỉ quyết định **span** (khoảng ký tự + heading path). Một hàm dùng chung `build_chunks` biến span thành `DocumentChunk` giống hệt cho cả hai arm ("both arms emit identical fields", ADR-0003 D6).
@@SNIP src/knowledge_assistant/infrastructure/chunking/chunk_builder.py 72-90@@
@@SNIP src/knowledge_assistant/infrastructure/chunking/chunk_builder.py 91-109@@
  Đọc chậm: (1) `chunker_config` không được chứa `:` vì nó nằm trong ID. (2) `display_text = text[start:end]` — **nguyên văn** từ văn bản đã chuẩn hoá (để hiển thị/trích dẫn). (3) `content_hash` = SHA-256 của `display_text`; nếu đã thấy hash này trong **cùng tài liệu** thì **bỏ** chunk (`dropped += 1`). (4) `embed_text` = dòng heading path + dòng trống + nội dung đã **bỏ link** — thứ mà embedding nhìn thấy. (5) `chunk_id = f"{source_id}:{chunker_config}:{len(chunks):04d}"` — số thứ tự được đánh **sau** khi bỏ trùng nên liên tục và xác định.
- **Ví dụ ID thật:** `01:header-1600:0000` (Arm A) và `01:fixed-1600:0000` (Arm B), đọc từ `arm-a.jsonl`/`arm-b.jsonl` trong máy này (dữ liệu chưa commit, chỉ đọc). Chunk đầu Arm A có `char_start=0, char_end=1528`; Arm B `char_end=1600`.
- **`display_text` vs `embed_text`:** hiển thị giữ nguyên link Markdown; embedding thấy văn bản **đã bỏ link** và có **dòng heading path ở đầu** ("contextual chunk header", D5). Ví dụ đã chạy thử: `embed_text = 'T > S\n\n# T\n\n## S\n\nSee docs now.\n'`.
- **Tại sao heading path ở đầu:** đoạn "ngữ cảnh" giúp embedding biết chunk thuộc phần nào của tài liệu (ví dụ "Routing > Route constraints").
- **Pitfalls:** `[GENERAL]` thêm ngữ cảnh vào embed_text nhưng không vào display_text nghĩa là **offset** (`char_start/char_end`) luôn trỏ vào văn bản chuẩn hoá, không phải embed_text (quan trọng cho luật "hit" ở file 10).

### 1.4 Số liệu thật của hai arm
| | Arm A (header-aware) | Arm B (fixed-size) |
|---|---|---|
| Chunk | 733 | 859 |
| Kích thước (min / p50 / p90 / max, ký tự) | 89 / 1 178 / 1 527 / 1 600 | 207 / 1 600 / 1 600 / 1 600 |
| Chunk cắt qua khối code | 24 (3.27%) | 387 (45.05%) |
| Chunk trùng bị bỏ (theo `content_hash` trong cùng tài liệu) | 447 | 0 |
| Tài liệu chỉ có 1 chunk | không | #09, #29 |
Nguồn: log build trong báo cáo INGEST-004 ([REPO docs/reports/execution/INGEST-004.md:44-52]); khớp file thống kê trong máy này (`stats-arm-a.json`, `stats-arm-b.json`, chưa commit).
- **Đọc bảng:** Arm A có ít chunk **hơn nhưng nhỏ hơn 1 600** (vì cắt theo heading); Arm B luôn gần đầy (median = max = 1 600). "447 bị bỏ" ở Arm A đến từ các tài liệu lặp nhiều **phiên bản** của cùng bài (#13, #17, #23) và #11: bỏ 135 + 118 + 190 + 4 (đọc từ `stats-arm-a.json`).

---

## Level 2 — Intermediate

### 2.1 Arm A — thuật toán header-aware trong 5 bước
@@SNIP src/knowledge_assistant/infrastructure/chunking/header_aware.py 1-16@@
Tóm tắt lại bằng lời: (1) tách theo section H1–H3 (H4+ ở lại trong section cha); (2) section **quá nhỏ (< `min_chars`)** gộp với section **anh em kế tiếp** nếu vẫn ≤ `max_chars`; (3) section **quá lớn (> `max_chars`)** cắt theo khối: đoạn văn, code fence, bảng (nguyên khối), dòng heading — rồi gói tham lam vào các mảnh; (4) các mảnh liên tiếp của một section bị cắt có **overlap** ≤ 200 ký tự, bắt đầu ở ranh giới từ, không bao giờ chui vào giữa code fence; (5) tuỳ chọn `drop_heading_only`.
- **Hàm điều phối:**
@@SNIP src/knowledge_assistant/infrastructure/chunking/header_aware.py 60-75@@
- **Bước 2 (gộp section nhỏ):**
@@SNIP src/knowledge_assistant/infrastructure/chunking/header_aware.py 79-98@@
  Điều kiện anh em: `following.level == first.level and following.heading_path[:-1] == first.heading_path[:-1]` (cùng cấp, cùng cha). `heading_path[:-1]` là slice bỏ phần tử cuối. Chunk gộp lấy heading path của section **đầu tiên**.
- **Đã chạy thử offline** trên một tài liệu nhỏ (max 100, min 30, overlap 15; kích thước tính bằng `_size`, tức sau khi `trim`): `Intro` = 22 ký tự (nhỏ) **không** gộp với `Setup` = 151 vì gộp lại `_size(text, 9, 186)` = **175 > 100**; còn `Tiny` (12) + `Also tiny` (17) **được** gộp thành 31 ≤ 100 (cùng cha, cùng cấp) thành một chunk có heading path của `Tiny`. `Setup` (151 ký tự) bị cắt thành 2 mảnh chồng nhau 14 ký tự (tối đa 15, lùi tới đầu từ).
- **Tại sao:** giữ trọn ý trong một section khi có thể (đơn vị nghĩa tự nhiên), và tránh chunk quá nhỏ.
- **Pitfalls:** `[GENERAL]` gộp chỉ với section **kế tiếp** cùng cha; một section nhỏ đứng trước một section con (khác cấp) không gộp được — đúng nguyên nhân dẫn đến chunk chỉ có heading (2.5).

### 2.2 Bước 3–4: cắt section quá lớn, overlap, và bảo vệ code/bảng
@@SNIP src/knowledge_assistant/infrastructure/chunking/header_aware.py 102-118@@
  Đọc: `budget = maximum if not pieces else maximum - overlap` (mảnh đầu được đầy đủ `max`, các mảnh sau chừa chỗ cho overlap); khi thêm `unit` sẽ vượt ngân sách thì đóng mảnh hiện tại; nếu mảnh kết thúc bằng một dòng **heading** thì mang heading đó sang mảnh sau ("keep a heading with the block that follows it").
@@SNIP src/knowledge_assistant/infrastructure/chunking/header_aware.py 119-132@@
  Mảnh sau bắt đầu lùi lại `room` ký tự so với cuối mảnh trước (`room = min(overlap, maximum - (content_end - previous_end))`), rồi `layout.overlap_start` dời tới đầu từ:
@@SNIP src/knowledge_assistant/infrastructure/chunking/header_aware.py 222-237@@
  Ba quy tắc: trong bảng thì bắt đầu ở **hàng kế**; nếu đang giữa từ thì tiến tới hết từ; nếu rơi **vào giữa code fence** thì nhảy tới hết fence.
- **Bảng bị cắt:** hàng header lặp lại **chỉ trong `embed_text`** để `display_text` vẫn là lát cắt nguyên văn ([REPO src/knowledge_assistant/infrastructure/chunking/header_aware.py:153-159]).
- **Tại sao:** code và bảng mất nghĩa nếu bị chém đôi; đây là điểm khác biệt chính giữa hai arm.
- **Pitfalls:** `[GENERAL]` thuật toán có nhiều nhánh biên; repo có bộ test dài (`tests/unit/infrastructure/test_chunkers.py`). Với code phức tạp như `_split`, hãy đọc **test** trước để hiểu hành vi mong muốn.

### 2.3 Khối xây dựng: nhận diện heading và code fence
@@SNIP src/knowledge_assistant/infrastructure/chunking/markdown_structure.py 44-62@@
- **Ý tưởng:** duyệt từng dòng, theo dõi biến `fence` (`None` khi ngoài code). Trong code fence thì **bỏ qua** dòng bắt đầu bằng `#`, vì trong code đó là comment/preprocessor chứ không phải heading.
- **Đường dẫn heading** (`Guide > Setup`) được dựng bằng dict `path` theo cấp:
@@SNIP src/knowledge_assistant/infrastructure/chunking/markdown_structure.py 90-101@@
  `path[heading.level] = heading.text` ghi tên ở cấp hiện tại; `path.pop(deeper, None)` xoá các cấp sâu hơn; `tuple(path[level] for level in sorted(path) if level <= heading.level)` tạo heading path.
- **Tại sao:** Microsoft Learn dùng nhiều ví dụ C# có `#region`/`#if`; nếu coi đó là heading, cấu trúc sai.
- **Pitfalls:** `[GENERAL]` Markdown có nhiều biến thể (fence bằng `~~~`, fence dài hơn, fence không đóng); code xử lý `_closes` cho từng trường hợp ([REPO src/knowledge_assistant/infrastructure/chunking/markdown_structure.py:85-87]).

### 2.4 Bỏ link trong `embed_text` (nhưng không đụng code)
@@SNIP src/knowledge_assistant/infrastructure/chunking/chunk_builder.py 51-65@@
- **Ý tưởng:** `_LINK.sub(r"\1", text)` thay `[chữ](url)` bằng `chữ` (`\1` là nhóm bắt đầu tiên). Nhưng **trong code fence thì giữ nguyên** (danh sách `fences` tính bằng `fenced_ranges`).
- **Đã chạy thử:** `strip_links` trên `See [docs](http://a.example/x) and ![img](http://i.png "t") ok` + một fence chứa `[keep](http://k)` → `See docs and img ok` và fence **không đổi**.
- **Tại sao:** URL trong embedding chỉ là nhiễu; nhưng `[x](y)` trong code là cú pháp thật.

### 2.5 Chunk chỉ chứa dòng heading — quyết định D3a (một câu chuyện thật)
- **Sự việc `[REAL]`:** INGEST-002 tạo ra **19** chunk Arm A chỉ gồm dòng heading (ví dụ `## Additional resources` không nội dung). Vì D3 chỉ gộp section nhỏ với section anh em **kế tiếp**, một H2 đứng ngay trước H3 con của nó sẽ đứng riêng. Chúng (a) không thêm nội dung, (b) chiếm chỗ trong top-k, và (c) **nằm trong khoảng của section mong đợi** nên metric "section hit@5" sẽ tính là trúng → **hit giả có lợi cho Arm A**. [REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:27-33]
- **Quyết định của owner (25/09/2026, INGEST-004), trước khi có bất kỳ kết quả nào:** bỏ các chunk đó trước khi đánh ID (ID vẫn liên tục); Arm B không đổi. Arm A từ **752 → 733** chunk. Cấu hình: `"drop_heading_only": true` ([REPO config/chunking.json:5-12]).
- **Kiểm chứng:** báo cáo INGEST-004 đo "19 chunk khớp đúng predicate", "không chunk bị bỏ nào chồng lên section của blueprint nào", và script kiểm phủ có thể **fail** (thử bằng cách xoá các chunk #22 khỏi bản sao). [REPO docs/reports/execution/INGEST-004.md:35-37,76-79]
- **Bài học:** một quy tắc chunking có thể làm lệch **thước đo**, không chỉ chất lượng retrieval. Ghi rõ "quyết định trước khi có kết quả" để tránh nghi ngờ điều chỉnh theo kết quả (Goodhart, file 10).

### 2.6 Xác định và bất biến: vì sao chunk ID quan trọng
- `chunk_id = source_id:chunker_config:index` — xác định vì thứ tự chunk cố định theo văn bản và số thứ tự đánh sau khi bỏ trùng (`f"{len(chunks):04d}"`). ID này là khoá của **idempotency** ở index (file 05 §2.3) và của cache.
- **Pitfalls:** `[REAL]` khi D3a bỏ 19 chunk, các ID phía sau bị **đánh số lại** (`09:header-1600:0001` từng bị bỏ và ID của nó giờ chỉ chunk cũ `0002`) — một ghi chú trong `spot-check.md` phải cập nhật. [REPO docs/reports/execution/INGEST-004.md:22-23,110] Đây là lý do "ID không phải khoá tự nhiên lâu dài" nếu quy tắc chunking đổi.

---

## Level 3 — Advanced

### 3.1 Retrieval: top-k, over-fetch và khử trùng theo *passage*
- **Vấn đề `[REAL]`:** corpus có nhiều **phiên bản** cùng một bài (doc #13, #17, #23). Nhiều chunk có văn bản **giống hệt** trừ URL trong link, nên `content_hash` (băm `display_text` thô) khác nhau, nhưng "đoạn văn mà LLM thấy" (đã bỏ link) và vector thì **giống hệt** → nhiều bản sao chiếm hết top-5. Số đo: Arm A có 13 passage xuất hiện trong >1 chunk, 26 bản sao thừa (chỉ 2 nếu tính theo `content_hash`); doc #17 riêng 19 bản sao. Arm B: 0. [REPO docs/specs/retrieval-spec.md:17-21]
- **Cách giải (quyết định của owner 2026-09-26):** lấy `top_k + overfetch` (5 + 10 = 15) hit, sắp theo (`score` giảm dần, `chunk_id` tăng dần), giữ hit **đầu tiên** của mỗi `passage_hash`, cắt còn `top_k`, đánh lại rank 1..k. Hit được giữ ghi lại `duplicate_chunk_ids`.
@@SNIP src/knowledge_assistant/application/retrieval/retrieve.py 29-45@@
  `passage_hash` khác `content_hash`:
@@SNIP src/knowledge_assistant/application/common/passage.py 12-19@@
- **Đã chạy thử:** hai chunk giống nhau chỉ khác URL (`http://a` vs `http://b`) → `content_hash` **khác**, `passage_hash` **giống** (`False`, `True`). Với 4 hit `(c1,0.9,P) (c2,0.8,P) (c4,0.7,R) (c3,0.7,Q)`, `top_k=2` → giữ `c1` (kèm `duplicate_chunk_ids=('c2',)`) và `c3` (hoà điểm với c4 nhưng "c3" < "c4"); `dropped = 1`.
- **Tại sao over-fetch:** nếu chỉ lấy top-5 rồi khử trùng, có thể còn 2–3 đoạn duy nhất; lấy dư 10 để sau khử trùng vẫn đủ 5 đoạn khác nhau.
- **Hiệu ứng phụ đã ghi nhận:** bản nào được giữ phụ thuộc điểm (hoà thì `chunk_id` nhỏ nhất); với cặp doc 12/13, bản được giữ có thể là bản mà một case liệt kê là *alternate* chứ không phải *expected*. Repo xử lý ở tầng metric (mọi span/source đều tính cả `duplicate_chunk_ids`, file 10). [REPO docs/specs/retrieval-spec.md:25-29]
- **Pitfalls:** `[GENERAL]` lấy dư số lượng (over-fetch) tốn thêm việc nhưng không tốn quota; số 10 là lựa chọn kinh nghiệm.

### 3.2 `Retriever.retrieve`
@@SNIP src/knowledge_assistant/application/retrieval/retrieve.py 65-80@@
  Kiểm tra bất biến ngay trong hàm: đúng **1** vector cho câu hỏi; store trả rỗng thì `RetrievalError` (không âm thầm trả kết quả trống). Trả `RetrievalResult` có `latency_ms` chia `embed_query` và `retrieve`.

### 3.3 Refusal gate: ngưỡng 0.686 suy ra như thế nào
- **Quy tắc (OD-9, 2026-09-26):** ngưỡng = (điểm top-1 **thấp nhất** trong các câu **trả lời được** của tập dev) − 0.05. Tune **chỉ trên dev** (`dev-v1.jsonl`, không phải tập eval), Arm A, dùng cho cả hai arm.
| Case | Ngôn ngữ | Trả lời được | Arm A top-1 | Arm B top-1 |
|---|---|---|---:|---:|
| Q-DEV-001 | en | có | 0.7360 | 0.7284 |
| Q-DEV-002 | vi | có | 0.7943 | 0.7882 |
| Q-DEV-003 | en | có | 0.7737 | 0.7646 |
| Q-DEV-004 | vi | có | 0.7548 | 0.7256 |
| Q-DEV-005 | en | không | 0.6741 | 0.6714 |
| Q-DEV-006 | vi | không | 0.6710 | 0.6707 |
[REPO docs/specs/retrieval-spec.md:42-49]
- 0.7360 − 0.05 = **0.6860**: tại giá trị này gate từ chối cả hai câu không trả lời được và không câu trả lời được nào. Biên: lệch 0.06 giữa thấp nhất (0.7360) và cao nhất của nhóm không trả lời được (0.6741). `score == threshold` thì **qua** (dùng `<` chặt). [REPO docs/specs/retrieval-spec.md:34-56]
- **Trong code:** mặc định `insufficient_score_threshold=float(os.getenv("INSUFFICIENT_SCORE_THRESHOLD", "0.686"))` ([REPO src/knowledge_assistant/config.py:210]); gate ở [REPO src/knowledge_assistant/application/generation/answer_question.py:90]; chế độ chẩn đoán `--gate-off` đặt ngưỡng `-inf` ([REPO src/knowledge_assistant/composition.py:70]) — **không dùng khi đánh giá**.
- **Tại sao:** tiết kiệm request LLM (500 RPD) và tránh để LLM "bịa" khi retrieval yếu.
- **Pitfalls `[REAL]`:** n = 6 câu dev (chỉ 2 câu trả lời được mỗi ngôn ngữ); spec tự ghi "n is small". README/worklog liệt kê "Re-tune the retrieval gate threshold per arm" là việc nên làm tiếp: ngưỡng chỉ tune trên Arm A. [REPO AI_WORKLOG.md:891-892]
- **Pitfalls `[GENERAL]`:** ngưỡng điểm cosine phụ thuộc model embedding và phân phối tài liệu — không dùng lại ngưỡng khi đổi model.

### 3.4 Những failure mode ADR dự đoán trước (đối chiếu khi đọc kết quả)
Mixed-version answers (#13/#17/#23); near-duplicate chunk chiếm top-k; fixed-size tách code khỏi phần giải thích; các section toàn link (#09, #08) bị lôi ra như nhiễu; tài liệu rất nhỏ (#09, #22, #29) chỉ là một chunk; tài liệu lớn lấn át tài liệu nhỏ. [REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:63-69] Hai trong số này đã thấy trong số liệu ở 1.4 (code fence bị cắt; #09/#29 một chunk ở Arm B).

### 3.5 "Cùng đầu vào, cùng thứ tự": phá hoà bằng `chunk_id`
`sorted(hits, key=lambda hit: (-hit.score, hit.chunk.chunk_id))` ([REPO src/knowledge_assistant/application/retrieval/retrieve.py:31]): khi hai điểm bằng nhau, thứ tự do `chunk_id` quyết định, nên hai lần chạy cho cùng kết quả — điều kiện để thí nghiệm A/B tái lập được.

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Fixed-size `size=20`, `overlap=5` trên văn bản 48 ký tự tạo bằng `"".join(f"w{i:02d} " for i in range(12))`. Cửa sổ bắt đầu ở đâu (trước khi `trim`)? Vì sao span đầu là `(0,19)` chứ không phải `(0,20)`?
<details><summary>Đáp án</summary>
`step = 20 − 5 = 15` → cửa sổ ở 0, 15, 30. Cửa sổ 0 là `[0,20)`; ký tự thứ 19 là khoảng trắng nên `trim` lùi `end` còn 19 → `(0,19)`. Tương tự `(16,35)` (đầu cũng bị `trim`) và `(30,47)` (đã chạy `FixedSizeChunker.spans`). Đọc [REPO src/knowledge_assistant/infrastructure/chunking/fixed_size.py:36-49] và `trim` ở [REPO src/knowledge_assistant/infrastructure/chunking/chunk_builder.py:35-41].
</details>

**B2 (Basic).** Tách `chunk_id = "01:header-1600:0000"` thành 3 phần và nói mỗi phần là gì. Vì sao `chunker_config` không được chứa `:`?
<details><summary>Đáp án</summary>
`["01", "header-1600", "0000"]` = `source_id`, `chunker_config`, chỉ số chunk (4 chữ số, đánh sau khi bỏ trùng). Nếu `chunker_config` chứa `:` thì không tách ID được; `build_chunks` ném `ValueError` để chặn ([REPO src/knowledge_assistant/infrastructure/chunking/chunk_builder.py:75-76]).
</details>

**B3 (Basic).** Từ bảng 1.4, tính lại `24/733` và `387/859` thành phần trăm.
<details><summary>Đáp án</summary>
24/733 = 3.27%; 387/859 = 45.05% (khớp báo cáo). Arm B cắt qua code gấp ~14 lần.
</details>

**I1 (Intermediate).** Chạy đoạn sau trong `.venv` (offline) và giải thích từng chunk của mỗi arm:
```python
from knowledge_assistant.infrastructure.parsing.markdown_normalizer import section_spans
from knowledge_assistant.core.models import Document, ParsedDocument
from knowledge_assistant.infrastructure.chunking.header_aware import HeaderAwareChunker, HeaderAwareConfig
from knowledge_assistant.infrastructure.chunking.fixed_size import FixedSizeChunker, FixedSizeConfig
text = ("# Guide\n\n## Intro\n\nShort intro.\n\n## Setup\n\nInstall the tool first. Then configure it carefully. "
        "Then run the tool once to check. Finally read the logs.\n\n```\ncode line 1\ncode line 2\n```\n\n"
        "## Tiny\n\nHi.\n\n## Also tiny\n\nYo.\n")
doc = ParsedDocument(Document("99", "d"), text, "Guide", None, "", tuple(section_spans(text)), True)
for c in HeaderAwareChunker(HeaderAwareConfig("header-100", 100, 30, 15)).chunk(doc): print("A", c.chunk_id, c.char_start, c.char_end, c.heading_path)
for c in FixedSizeChunker(FixedSizeConfig("fixed-100", 100, 15)).chunk(doc): print("B", c.chunk_id, c.char_start, c.char_end, c.heading_path)
```
<details><summary>Đáp án (đã chạy)</summary>
Arm A: 5 chunk — `0000` `(0,7)` heading `Guide` (chỉ dòng `# Guide`; ở đây `drop_heading_only` mặc định `False`); `0001` `(9,31)` `Guide > Intro`; `0002` `(33,128)` và `0003` `(114,184)` cùng `Guide > Setup` (section 151 ký tự bị cắt, chồng nhau 14 ký tự [114..128)); `0004` `(186,217)` `Guide > Tiny` gộp cả "Also tiny". Arm B: 3 chunk `(0,100)`, `(85,184)`, `(170,217)` — cửa sổ cứng, heading path = heading gần nhất trước điểm bắt đầu (`Guide`, `Guide > Setup`, `Guide > Setup`); chunk thứ 2 và 3 cắt giữa câu/giữa khối code.
</details>

**I2 (Intermediate).** Vì sao `Intro` không gộp với `Setup` ở I1 dù `Intro` nhỏ hơn `min_chars`?
<details><summary>Đáp án</summary>
Điều kiện gộp có hai vế: section kế tiếp là **anh em** và kích thước gộp `_size(text, start, following.char_end) <= max_chars`. Gộp `Intro`(22)+`Setup`(151): `_size(text, 9, 186)` = 175 > 100 nên `break` ([REPO src/knowledge_assistant/infrastructure/chunking/header_aware.py:90-96]).
</details>

**I3 (Intermediate).** Hai chunk khác nhau chỉ ở URL trong một link Markdown: `content_hash` và `passage_hash` giống hay khác? Điều đó ảnh hưởng gì đến retrieval?
<details><summary>Đáp án</summary>
`content_hash` **khác** (băm `display_text` thô), `passage_hash` **giống** (băm phần thân đã bỏ link). Retrieval khử trùng bằng `passage_hash` nên chỉ giữ một bản, tránh top-k bị chiếm bởi các bản sao mà LLM thấy y hệt ([REPO src/knowledge_assistant/application/common/passage.py:12-19]).
</details>

**A1 (Advanced).** Nếu chọn ngưỡng theo **Arm B** (lấy điểm thấp nhất trong các câu trả lời được của Arm B, trừ 0.05), ngưỡng là bao nhiêu và gate có từ chối đúng hai câu không trả lời được của Arm B không?
<details><summary>Đáp án</summary>
Thấp nhất của Arm B (câu trả lời được) là 0.7256 (Q-DEV-004) → ngưỡng `0.7256 − 0.05 = 0.6756`. Hai câu không trả lời được của Arm B có top-1 0.6714 và 0.6707, đều `< 0.6756` → bị từ chối. Tức là trên dev, một ngưỡng riêng cho Arm B cũng hợp lệ nhưng khác (0.6756 vs 0.686); repo dùng **một** ngưỡng chung (tune trên Arm A) — hạn chế được ghi trong "With 7 more days" ([REPO AI_WORKLOG.md:891-892]).
</details>

**A2 (Advanced).** Vì sao `dedupe_by_passage` đếm `dropped = len(ordered) - len(kept)` (kể cả các hit bị bỏ nằm ngoài top-k) thay vì chỉ đếm trong top-5?
<details><summary>Đáp án</summary>
Để `duplicates_dropped` phản ánh **số bản sao đã bị loại trong toàn bộ tập over-fetch** — số liệu chẩn đoán cho biết hiện tượng trùng lặp lớn đến đâu (spec: "including drops whose kept hit falls outside the top k") ([REPO docs/specs/retrieval-spec.md:23-24]). Lưu ý `kept` là dict theo `passage_hash` nên đếm theo số passage duy nhất.
</details>

**A3 (Advanced, đọc code).** Trong `_split`, vì sao mảnh đầu dùng `budget = maximum` còn mảnh sau `maximum − overlap`?
<details><summary>Đáp án</summary>
Mảnh sau sẽ được **thêm** một đoạn overlap (≤ 200 ký tự) ở đầu, nên phần nội dung mới của nó phải nhỏ hơn để tổng vẫn ≤ `max_chars`; mảnh đầu không có overlap nên dùng đủ `max`. Chính docstring cũng nói overlap "is shortened so a piece stays within `max_chars`" ([REPO src/knowledge_assistant/infrastructure/chunking/header_aware.py:12-13,107]).
</details>

## Self-check questions
1. Chunk quá lớn / quá nhỏ gây vấn đề gì?
2. Arm A và Arm B khác nhau chính xác ở đâu, và giữ cố định những gì?
3. `display_text` khác `embed_text` thế nào, vì sao?
4. `content_hash` vs `passage_hash`: dùng khi nào?
5. Vì sao lấy `top_k + overfetch` rồi mới khử trùng?
6. Công thức ngưỡng gate; vì sao dùng "− 0.05"?
7. Vì sao D3a được quyết định **trước** khi có kết quả?

## Interview Q&A
1. **"Bạn chọn kích thước chunk như thế nào?"** — Dựa trên phân phối đo được của corpus (không dựa kết quả retrieval), ghi trong ADR-0003 D3; mọi thay đổi phải qua ADR mới/amendment có bằng chứng ([REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:82]).
2. **"Header-aware chunking hơn gì fixed-size?"** — Không cắt code/bảng (3.27% vs 45.05% chunk cắt qua code), giữ ngữ cảnh heading; đổi lại phức tạp hơn và chunk không đều ([REPO docs/reports/execution/INGEST-004.md:44-52]).
3. **"Xử lý tài liệu trùng lặp thế nào?"** — Bỏ trùng `content_hash` lúc chunk (447 ở Arm A), và khử trùng theo `passage_hash` lúc retrieval với over-fetch ([REPO docs/specs/retrieval-spec.md:14-21]).
4. **"Làm sao quyết định ngưỡng từ chối?"** — Công thức trên dev, có bảng số; thừa nhận n nhỏ và chỉ tune trên Arm A ([REPO docs/specs/retrieval-spec.md:38-56]).
5. **"Một quyết định thiết kế có thể làm lệch thước đo — ví dụ?"** — Chunk chỉ chứa heading tạo hit giả cho Arm A; D3a loại bỏ, quyết định trước khi có kết quả ([REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:27-33]).

## Further reading
- LangChain / LlamaIndex text splitters (khái niệm recursive / structure-aware splitting); Pinecone/Weaviate blog về chunking strategies — đọc như bối cảnh, không phải tài liệu của repo. `[GENERAL]`
- Markdown spec: CommonMark (fenced code blocks, ATX headings). `[GENERAL]`
- Tiếp theo: 08 (prompt & generation), rồi [09 — LLM API](09-llm-api-engineering.md).
