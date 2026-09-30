# 10 · Thiết kế đánh giá: bộ câu hỏi eval-v1, đóng băng, tách dev/eval, luật hit, metric và mẫu số, tính hợp lệ
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [05](05-rag-fundamentals.md), [07](07-chunking-and-retrieval.md), [08](08-generation-and-prompting.md) · Study time: ~10–12h · Home file của: ground truth, dev vs eval split, freeze (`eval-freeze-v1` + hash), evidence slot, source/section hit@k (lenient/strict), MRR, evidence hit, luật trùng lặp (duplicate rule), nhãn kết quả (OD-5), points-covered, mẫu số (answerable / unanswerable / answered), bias & validity, coverage matrix
> Bài tập chạy được: `learning/_tools/exercises/eval_metrics_scenarios.py` (offline, không mạng, không key).

## Vì sao file này quan trọng trong dự án
Đề bài yêu cầu ≥ 30 câu hỏi và một thí nghiệm ≥ 2 cách tiếp cận ([REPO CLAUDE.md:5]). Nhưng "đánh giá" dễ nhất là **tự lừa mình**: viết câu hỏi sau khi thấy hệ thống trả lời gì, chọn metric thuận lợi, chỉnh ngưỡng theo bộ test. Toàn bộ thiết kế eval-v1 là một chuỗi quyết định để **không thể** lừa mình: đáp án chuẩn (ground truth) viết **trước** khi có index, bộ câu hỏi bị **đóng băng bằng hash**, có bộ dev **tách hẳn** để chỉnh prompt, mọi metric có **mẫu số** được ghi rõ, và mọi thay đổi luật sau khi freeze phải là một **amendment** có log. Bạn sẽ học cách nghĩ này nhiều hơn là công thức.

---

## Level 1 — Basic

### 1.1 Đánh giá một hệ thống RAG đo cái gì
- **Ý tưởng:** bốn chiều: chất lượng **câu trả lời**, chất lượng **truy xuất** (retrieval), chất lượng **citation**, và **độ trễ**. [REPO docs/specs/evaluation-spec.md:7]
- **Mỗi case gồm:** câu hỏi, đáp án kỳ vọng/ground truth, nguồn kỳ vọng, câu trả lời sinh ra, kết quả. [REPO docs/specs/evaluation-spec.md:6]
- **C# analogy:** giống một bộ **integration test có dữ liệu kỳ vọng** (golden files), nhưng "assert" không phải `==` mà là các nhãn + tỉ lệ, vì đầu ra là ngôn ngữ tự nhiên.
- **Tại sao nhiều chiều:** một hệ thống có thể trả lời đúng nhưng trích sai nguồn (không tin cậy), hoặc truy xuất đúng nhưng model bỏ qua (lỗi ở generation). Tách chiều mới chỉ ra được **lỗi ở tầng nào** (file 13 làm điều này).

### 1.2 Ground truth phải có trước, và không phụ thuộc hệ thống
- **Quy tắc dự án:** ground truth (source_id kỳ vọng + heading path) được viết **trước khi build index**; không bịa kết quả/điểm/latency ([REPO CLAUDE.md:13]).
- **Cách làm ra ground truth:** chọn section từ bản kiểm kê corpus, **đọc trọn section**, mỗi đáp án lấy từ chính văn bản section đó (không search web, không kiến thức của model); mỗi case có **đoạn trích nguyên văn** (evidence quote ≤ 300 ký tự) gắn với các *answer point* mà nó chứng minh. [REPO docs/specs/evaluation-dataset-design.md:82-94]
- **Tại sao:** nếu ground truth sinh ra từ đầu ra của hệ thống thì đánh giá là **vòng tròn (circular)** — hệ thống luôn "đúng". Repo còn kiểm bằng test: mỗi required point phải có ít nhất một quote chống lưng ([REPO docs/specs/evaluation-dataset-design.md:91]).
- **Pitfalls `[GENERAL]`:** nhờ một LLM sinh câu hỏi + đáp án rồi dùng chính nó chấm là mẫu circular kinh điển; ở repo này người viết ground truth là chủ dự án + trợ lý theo blueprint, và có bản review độc lập.

### 1.3 Hai bộ câu hỏi: dev (chỉnh) và eval (báo cáo)
- **Con số:** bộ **eval** 36 case = 28 single-source + 4 cross-document (32 answerable) + 4 "không có trong tài liệu"; 18 tiếng Anh + 18 tiếng Việt; bộ **dev** 6 case, **rời nhau** với eval, chỉ dùng chỉnh prompt và luật "insufficient", **không bao giờ báo cáo**. [REPO docs/specs/evaluation-spec.md:20-26]
- **Đã kiểm trên dữ liệu thật:** `eval-v1.jsonl` có 36 dòng (`scope`: 28/4/4; `language`: 18/18; `split`: toàn `eval`); `dev-v1.jsonl` 6 dòng ([REPO data/evaluation/questions/eval-v1.jsonl:1-1], [REPO data/evaluation/questions/dev-v1.jsonl:1-1]; đếm bằng một đoạn Python ngắn, chạy được).
- **C# analogy:** train/validation/test — ở đây "dev" = tập chỉnh tham số, "eval" = tập kiểm tra cuối. Chỉnh trên eval là **rò rỉ dữ liệu (data leakage)**.
- **Tại sao:** nếu bạn chỉnh prompt cho tới khi điểm eval cao thì điểm đó không còn là ước lượng trung thực. Dev set tồn tại để chỗ chỉnh có "của riêng".
- **Pitfalls `[REAL]`:** ngưỡng cổng truy xuất 0.686 được chọn trên điểm dev của **Arm A**, rồi áp cho cả hai arm; báo cáo thí nghiệm thừa nhận đây là mối đe doạ tới tính hợp lệ (xem 3.2). [REPO docs/reports/epics/EPIC-06-experiment.md:87-91]

### 1.4 Sáu nhãn kết quả (OD-5)
Mỗi câu trả lời nhận **đúng một** nhãn:
@@SNIP docs/specs/evaluation-spec.md 28-38@@
- **Đọc chậm:** ba nhãn cho câu **có đáp án** (`correct`/`partially_correct`/`incorrect`) + `false_refusal` (hệ thống từ chối trong khi tài liệu có đáp án); hai nhãn cho câu **không có đáp án** (`correct_refusal`/`hallucination`).
- **Tại sao tách `false_refusal`:** từ chối nhầm và trả lời sai là hai lỗi khác hẳn (bỏ lỡ vs bịa). Gộp lại sẽ che cái này bằng cái kia (liên hệ hai lớp "insufficient", file 08 §1.2).
- **Pitfalls:** `[GENERAL]` một hệ thống "từ chối mọi thứ" có `hallucination = 0` nhưng vô dụng; luôn đọc cặp (`false_refusal_rate`, `hallucination_rate`) cùng nhau.

### 1.5 Retrieval metric cơ bản: hit@k và MRR
- **hit@k:** câu hỏi được coi là "trúng" nếu **trong k chunk đầu** có chunk chứa/nằm trong phần kỳ vọng. Dự án dùng **k = 5** làm headline, báo thêm @1 và @3. [REPO src/knowledge_assistant/application/evaluation/metrics/retrieval.py:27]
- **MRR (Mean Reciprocal Rank):** với mỗi câu, lấy `1 / hạng` của chunk trúng đầu tiên (0 nếu không có), rồi lấy trung bình. Trúng ở hạng 1 → 1.0; hạng 3 → 0.333.
- **Đã chạy thử offline** (`eval_metrics_scenarios.py`, mục E3–E4): chunk trúng ở hạng 3 → MRR = `0.3333`; không chunk nào trúng → `0.0`; ca một slot với chunk trúng ở hạng 3 cho `hit@1, @3, @5 = [0, 1, 1]`.
- **Tại sao cả hai:** hit@5 hỏi "có tìm được không" (đủ để LLM thấy bằng chứng); MRR hỏi "tìm được **sớm** không" (top-1 quan trọng khi prompt dài, chi phí token).
- **Pitfalls `[GENERAL]`:** hit@k **không** đo xem model có *dùng* bằng chứng đó không; đó là việc của chỉ số câu trả lời/citation.

---

## Level 2 — Intermediate

### 2.1 Section hit dựa trên **offset ký tự**, không so tên heading
- **Ý tưởng:** ground truth nói "bằng chứng nằm ở section *Service lifetimes* của tài liệu #10". Retrieval trả các chunk có `[char_start, char_end)`. Chunk "trúng" section nếu **cùng `source_id` và hai khoảng ký tự chồng lấn** — **không** so chuỗi heading. Lý do: Arm A gắn nhãn một section nhỏ được gộp bằng heading của section đầu (ADR-0003 D3), còn Arm B dùng heading gần nhất phía trước (D5); cùng một chữ có thể mang heading khác nhau. [REPO src/knowledge_assistant/application/evaluation/metrics/retrieval.py:3-5]
- **Trong code:**
@@SNIP src/knowledge_assistant/application/evaluation/metrics/spans.py 15-25@@
@@SNIP src/knowledge_assistant/application/evaluation/metrics/retrieval.py 63-65@@
  `overlaps` dùng **khoảng nửa mở** `[a, b)`: hai khoảng chỉ *chạm nhau* (`[0,10)` và `[10,20)`) **không** chồng lấn. Đã chạy thử: `overlaps(0,10,10,20)` → `False`, `overlaps(0,10,9,20)` → `True`, `overlaps(5,6,0,100)` → `True` (mục E1).
- **Đọc chậm:** `max(a_start, b_start) < min(a_end, b_end)` — đoạn giao là `[max(start), min(end))`, khác rỗng khi start lớn hơn nhỏ hơn end. `@dataclass(frozen=True)` ≈ `record` bất biến (file 01).
- **Tại sao:** section hit phải bền với cách mỗi arm cắt chunk khác nhau; offset là "ngôn ngữ chung". **Đây cũng là lý do ground truth có bản đồ span** `expected-spans-v1.json` ([REPO data/evaluation/questions/expected-spans-v1.json:1-1]) tính sẵn từ bản văn bản đã chuẩn hoá.
- **Pitfalls `[GENERAL]`:** off-by-one ở ranh giới nửa mở là lỗi kinh điển; luôn viết test chạm-nhau (`[0,10)` vs `[10,20)`).

### 2.2 Evidence slot: "tất cả các slot, một nguồn bất kỳ trong slot"
- **Ý tưởng:** một số câu cần **hai** nguồn (cross-document). Mỗi nguồn kỳ vọng và nguồn thay thế thuộc một **slot** (`S1`, `S2`…). Một case "trúng" khi **mọi slot** đều có ít nhất một nguồn của slot đó trong top-5. Slot thứ hai vẫn có thể được thoả bởi một nguồn **thay thế** hợp lệ. [REPO docs/specs/evaluation-spec.md:49-54]
- **Ví dụ trong spec:** S1 = {#04 kỳ vọng}, S2 = {#26 kỳ vọng, #20 thay thế}; top-k = {#04, #20} → **lenient trúng, strict trượt**. [REPO docs/specs/evaluation-spec.md:58]
- **Trong code:**
@@SNIP src/knowledge_assistant/application/evaluation/metrics/retrieval.py 98-104@@
@@SNIP src/knowledge_assistant/application/evaluation/metrics/retrieval.py 107-114@@
- **Đọc chậm:** `{slot: any(...) for slot in sorted({...})}` là **dict comprehension** lồng `any(... for chunk ... for span ...)`; `all(....values())` cuối cùng nghĩa là "mọi slot đều True". `key=lambda s: int(s[1:])` sắp `S2` trước `S10` (không sắp theo chuỗi).
- **Đã chạy thử offline** (mục E2, đúng ví dụ trên với offset giả): lenient source/section = `1`; strict = `0`; `slots = {'S1': True, 'S2': True}`, `fraction = 1.0`.
- **Tại sao:** "tất cả slot" phản ánh câu cần cả hai mảnh thông tin; "một trong slot" cho phép các nguồn đồng nghĩa hợp lệ mà không phạt hệ thống.
- **Pitfalls `[REAL]`:** ban đầu spec để mở "cross-document: cần tất cả hay một trong?" — chủ dự án quyết (D1, 24/09/2026) là evidence slot. [REPO docs/specs/evaluation-dataset-design.md:183]

### 2.3 Lenient (headline) và strict (luôn báo kèm)
- **Quy tắc:** lenient = nguồn kỳ vọng **hoặc thay thế**; strict = **chỉ** nguồn kỳ vọng. Headline là lenient; strict luôn nằm cạnh. Nếu kết luận **đảo chiều** giữa strict và lenient thì báo cáo **phải nói**. [REPO docs/specs/evaluation-spec.md:55-61]
- **Trong code:** `_usable(spans, strict)` lọc bỏ span `ALTERNATE` khi `strict=True`. [REPO src/knowledge_assistant/application/evaluation/metrics/retrieval.py:94-95]
- **Tại sao có điều kiện này:** chủ dự án nới các nguồn thay thế sau một đợt kiểm lại; điều kiện đi kèm là **báo cả hai** để không ai nghi "nới luật cho đẹp số" (OWNER-001, 25/09/2026).
- **Đã chạy thử offline** (mục E3): "strict MRR" khi chunk đầu tiên chỉ là nguồn thay thế (doc 20) và chunk kỳ vọng ở hạng 2 → `0.5`; lenient sẽ là `1.0`.
- **Pitfalls `[GENERAL]`:** khi bạn đổi luật chấm **sau khi thấy kết quả**, luôn giữ luật cũ chạy song song. Đây là "report both" thay vì "chọn cái đẹp".

### 2.4 Luật trùng lặp (duplicate rule): section-level khác source-level
- **Vấn đề `[REAL]`:** retriever chỉ giữ một chunk cho mỗi `passage_hash` (file 07). Chunk được giữ có thể nằm ở tài liệu *kia* của cặp #12/#13 (hai tài liệu có đoạn giống nhau). Nếu chỉ nhìn chunk được giữ, một truy xuất đúng bị chấm trượt.
- **Quyết định (chủ dự án, 27/09/2026):** với metric **section** (hit, MRR, slot fraction, citation section precision), chunk "trúng" nếu **nó hoặc bất kỳ bản trùng bị loại** của nó chồng lấn span. Với metric **source**, chỉ dùng **tài liệu của chunk được giữ** (cái người dùng thực sự thấy). Bản đầu ghi "span/source" là **lỗi từ ngữ**, chủ dự án sửa thành chỉ section. [REPO docs/specs/evaluation-spec.md:62]
- **Trong code:**
@@SNIP src/knowledge_assistant/application/evaluation/metrics/retrieval.py 86-91@@
- **Đã chạy thử offline** (mục E5): chunk giữ ở doc `12` có bản trùng ở doc `13`, span kỳ vọng ở doc `13` → **section hit = 1, source hit = 0**. (Mục E6: cùng doc nhưng offset khác → section = 0, source = 1.)
- **Tác động thực tế:** báo cáo thí nghiệm ghi luật này làm đổi **0** giá trị metric ở cả hai arm; mọi bản trùng bị loại xếp hạng 6–15, ngoài top-5. [REPO docs/reports/epics/EPIC-06-experiment.md:93-96]
- **Pitfalls:** đây là ví dụ đẹp về **một luật đã viết vào tài liệu, có test, và sau này được đo xem có ảnh hưởng không** — thay vì tranh luận.

### 2.5 Evidence hit: kiểm ở tầng **nội dung**
- **Ý tưởng:** ngoài trúng theo vị trí, đo xem **mọi required point** có ít nhất một *quote* chứng minh nó nằm **nguyên văn** trong một chunk top-k (all-of qua các point, any-of qua các quote của một point; khoảng trắng được gộp như `validate_questions.py`). Quote của optional point bị bỏ qua. [REPO docs/specs/evaluation-spec.md:63]
- **Tại sao thêm metric này:** "trúng section" cho biết chunk *ở đúng chỗ*, nhưng chunk có thể chỉ chứa nửa đầu section; evidence hit hỏi "bằng chứng cần thiết có nằm **trong văn bản chunk mà LLM thấy** không". Nó cũng bám lenient, không bám strict.
- **Chẩn đoán kèm:** `evidence_hit_via_alternate_only` (trúng nhờ chunk từ section thay thế); 4 trong 32 case eval có thể đạt điều đó (003, 004, 007, 008). [REPO docs/specs/evaluation-spec.md:63]
- **Pitfalls `[GENERAL]`:** khớp chuỗi nguyên văn nhạy với chuẩn hoá (khoảng trắng, xuống dòng, link Markdown). Repo khớp trên `display_text` (còn link) sau chuẩn hoá giống nhau, **không** trên `embed_text` (link bị rút gọn). [REPO docs/specs/evaluation-dataset-design.md:92]

### 2.6 Bảng ánh xạ `map_result`: nhãn do **code** chọn, judge chỉ cấp dữ liệu
- **Ý tưởng:** judge (LLM) **không** chọn nhãn; nó điền các trường dữ liệu (coverage của từng point, có mâu thuẫn không, claim không được hỗ trợ, có "trình bày nội dung liên quan như đáp án" không). Một hàm thuần, xác định (`map_result`) ánh xạ ra nhãn. Thiếu dữ liệu cần thiết → `JudgeVerdictMissing`, **không** đoán.
@@SNIP src/knowledge_assistant/application/evaluation/metrics/mapping.py 50-71@@
- **Đọc chậm:** nhánh `not answerable` (tài liệu không có đáp án): từ chối "trơn" (không note, không citation) → `correct_refusal` **không cần judge**; còn lại cần kiểm từ chối. Nhánh `answerable`: `insufficient` → `false_refusal`; ngược lại nhìn coverage: mâu thuẫn → `incorrect`; mọi point `yes` → `correct`; có ít nhất một `yes/partial` → `partially_correct`; còn lại `incorrect`.
- **C# analogy:** một `switch` expression thuần trên một `record` (pattern matching). Cái hay là **chỗ quyết định nhãn được test bằng bảng**, độc lập với LLM.
- **Tại sao:** tách "cảm nhận của LLM" khỏi "luật chấm của dự án" làm cho luật **kiểm thử được, xác định, và thay đổi có kiểm soát** (file 11 đi sâu vào phía judge).
- **Pitfalls:** `[GENERAL]` nếu để LLM chọn thẳng nhãn, cùng một câu trả lời có thể được gán nhãn khác nhau giữa các lần chạy; đây là nguồn phương sai mà bảng ánh xạ loại bỏ.

### 2.7 Points-covered: điểm mịn hơn nhãn
- **Công thức:** `(số point required được judge "yes" + 0.5 × số point "partial") ÷ số point required`. Ví dụ `yes, partial, no` → `1.5/3 = 0.50`. Optional point không bao giờ tính, nên không thể hạ điểm. [REPO docs/specs/evaluation-spec.md:46]
- **Trong code:**
@@SNIP src/knowledge_assistant/application/evaluation/metrics/mapping.py 79-89@@
- **Tại sao:** nhãn 3 mức quá thô để so hai arm (một câu "partially_correct" có thể phủ 1/3 hoặc 2/3). Điểm mịn cho phép so sánh tinh hơn.
- **Đã chạy thử offline** (file 11 mục bài tập): `points_covered(["yes","partial","no"])` → `0.5`.
- **Pitfalls `[GENERAL]`:** `0.5` cho `partial` là **quy ước**, không phải chân lý; hãy ghi rõ như spec đã làm.

### 2.8 Mẫu số (denominator) — chỗ số liệu hay bị nói dối
Ba mẫu số **không được lẫn** ([REPO docs/specs/evaluation-spec.md:70]):
| Mẫu số | Là gì | Dùng cho |
|---|---|---|
| **answerable** | mọi record có đáp án đã gắn nhãn (kể cả khi hệ thống từ chối) | `accuracy`, `lenient_accuracy`, `false_refusal_rate` |
| **unanswerable** | mọi record corpus-insufficient đã gắn nhãn | `correct_refusal_rate`, `hallucination_rate` |
| **answered** | answerable trừ `false_refusal` (hệ thống thực sự trả lời) | mọi metric citation, `groundedness_rate`, `points_covered_mean` |
- **Trong code:**
@@SNIP src/knowledge_assistant/application/evaluation/scoring.py 207-217@@
@@SNIP src/knowledge_assistant/application/evaluation/scoring.py 224-231@@
- **Đọc chậm:** `count(group, *labels)` là hàm lồng dùng `*labels` (varargs) và biểu thức generator `sum(1 for ...)`; `_rate(numerator, denominator)` trả `{"n", "count", "value"}` — **luôn kèm `n`** để người đọc thấy mẫu số, và `value=None` khi mẫu số 0 (không chia cho 0).
- **Record lỗi và chưa gắn nhãn:** record **runner-error** (không có câu trả lời) bị loại khỏi mọi mẫu số và được **liệt kê riêng** — không tính đúng, không tính sai. Record chưa gắn nhãn vì `judge_error` chỉ bị loại khỏi các metric phụ thuộc judge; các metric kiểm span tự động vẫn tính chúng. [REPO docs/specs/evaluation-spec.md:70-76]
- **Sự cố `[REAL]`:** đoạn văn spec ban đầu nói record chưa gắn nhãn bị loại khỏi **mọi** mẫu số — sai; code (`summarize_citations` không lọc theo judge) mới đúng. Fix ở EVAL-003c-verify (28/09/2026): sửa **câu văn**, không sửa code. [REPO docs/specs/evaluation-spec.md:94-98]
- **Tại sao quan trọng:** báo cáo thí nghiệm ghi rõ accuracy của Arm A là `22/31 = 0.710` (ghép cặp) chứ không phải `23/32 = 0.719` (không ghép), vì `Q-EVAL-002:A` đúng nhưng không có đối tác B. [REPO docs/reports/epics/EPIC-06-experiment.md:80-81]
- **Pitfalls `[GENERAL]`:** "accuracy 71%" mà không nói 71% của cái gì là con số **vô nghĩa**. Luôn viết `n`.

---

## Level 3 — Advanced

### 3.1 Đóng băng (freeze): hash + tag + amendment log
- **Cơ chế 1 — tag Git:** bộ câu hỏi và ground truth được **đóng băng** ở tag `eval-freeze-v1` (commit "EVAL-002: eval-v1 ground truth frozen (owner-approved)", đọc bằng `git show`).
- **Cơ chế 2 — hash trong snapshot:** `docs/snapshots/evaluation/eval-v1.md` chứa SHA-256 từng file câu hỏi. **Trước mỗi lượt chạy**, runner tính lại hash và so — khác thì **từ chối chạy**:
@@SNIP src/knowledge_assistant/application/evaluation/integrity.py 13-22@@
@@SNIP src/knowledge_assistant/application/evaluation/integrity.py 25-39@@
- **Đọc chậm:** `_ROW.findall` trả **list tuple** `(tên_file, hash)` → dict comprehension. Hàm kiểm chạy trên **cả hai file** bất kể split nào được chạy ("a quiet edit to either one stops every run", docstring dòng 5-6). `raise IntegrityError(...)` nói thẳng: "a change must be a logged amendment, never a quiet edit".
- **Đã chạy thử offline** (mục E7): snapshot giả có hash của `b"line\n"` → `verify_frozen_files` trả dict hash; đổi thành `b"line \n"` (thêm một khoảng trắng) → `IntegrityError: ... SHA-256 is 2f3c20bc...`.
- **Cơ chế 3 — amendment log:** sau freeze mọi thay đổi **luật chấm** đều ghi trong spec: cái gì, tại sao, ngày. Ví dụ: evidence hit (26/09), duplicate rule (27/09), mẫu số (28/09). File câu hỏi **không đổi**; chỉ luật chấm đổi. [REPO docs/specs/evaluation-spec.md:87-98]
- **C# analogy:** giống **strong-name/checksum** cho một gói dữ liệu, cộng với một `CHANGELOG` bắt buộc.
- **Tại sao:** bạn không thể chứng minh mình *không* chỉnh câu hỏi cho hợp kết quả, nhưng bạn có thể làm cho việc chỉnh **bị phát hiện ngay** (hash không khớp).
- **Pitfalls `[GENERAL]`:** freeze không bảo vệ khỏi việc chỉnh **luật chấm**; vì vậy amendment phải có log và được báo cáo cùng kết quả.

### 3.2 Mối đe doạ tới tính hợp lệ (threats to validity) — repo tự liệt kê
Báo cáo thí nghiệm nêu thẳng các hạn chế. Đọc phần này như một mẫu "viết trung thực": [REPO docs/reports/epics/EPIC-06-experiment.md:85-122]
1. **Ngưỡng cổng chỉnh trên Arm A** (0.686) rồi áp cho cả hai; phân bố điểm của hai arm khác nhau nên một quyết định gần ngưỡng là đo *độ khớp của ngưỡng*, không chỉ chất lượng chunk (`Q-EVAL-001` là ví dụ).
2. **Dedup chỉ tác động Arm A** (Arm B không có nhóm trùng) — nhưng đã đo: 0 giá trị đổi.
3. **Judge là chính model trả lời** (self-preference); spot-check của chủ dự án 10 verdict: 8/10 nhãn khớp (κ 0.69), 9/10 theo "đồng ý với judge không" — n = 10 nhỏ. 2/61 lời gọi judge lỗi định dạng, cả hai trên `Q-EVAL-002:B`.
4. **n = 36 nhỏ:** với 31 cặp có nhãn chỉ 5 cặp bất đồng ở accuracy; ngay cả 5–0 cũng chỉ cho `p = 0.0625`. "Không khác biệt đáng tin" nghĩa là "quá ít bất đồng để kết luận", **không** phải "hai arm bằng nhau".
5. **Độ trễ bị nhiễu bởi thứ tự chạy và cache** (Arm B toàn cache hit nên `embed_query` p50 0.1 ms so với 352 ms).
6. **Mỗi arm chỉ chạy một lần** — không tách được phương sai sinh câu trả lời khỏi hiệu ứng chunker.
- **Tại sao:** đọc phần này trước khi tin bất kỳ con số nào ở file 13; nó cho thấy khác biệt giữa "có số" và "có bằng chứng".
- **Goodhart `[GENERAL]`:** "khi một thước đo trở thành mục tiêu thì nó thôi là thước đo tốt". Chỉnh ngưỡng trên bộ có số liệu chính là ví dụ nhỏ; dev/eval tách biệt là biện pháp.

### 3.3 Kiểm soát thiên lệch (bias controls) trong thiết kế bộ câu hỏi
- Bộ câu hỏi trộn ca mà ranh giới section **nên** giúp (heading cụ thể, bảng, code cạnh giải thích) với ca mà độ tương tự thuần **đủ**; **không** case nào được viết để thiên vị một arm; tham số đóng băng; **cùng** bộ câu hỏi cho cả hai arm. [REPO docs/specs/evaluation-dataset-design.md:114-118]
- **Bảng failure mode** ánh xạ mỗi chế độ lỗi mà ADR-0003 dự đoán (trộn phiên bản, chunk gần trùng chiếm top-5, cắt code khỏi phần giải thích, nhiễu danh sách link, tài liệu nhỏ, tài liệu lớn lấn át…) sang các case cụ thể — để thí nghiệm **thử** các dự đoán thay vì giả định. [REPO docs/specs/evaluation-dataset-design.md:56-68]
- **Nhóm song song EN/VI:** 7 nhóm (14 case) cùng nguồn, cùng answer point, cùng tiêu chí; một test kiểm chúng giống nhau — để tách **hiệu ứng ngôn ngữ** khỏi **độ khó**. Độ khó theo ngôn ngữ **không** bằng nhau (EN 3/10/5 dễ/vừa/khó; VI 4/7/7), nên so sánh ngôn ngữ chủ yếu trên tập song song. [REPO docs/specs/evaluation-dataset-design.md:15-21]
- **4 case "không có trong tài liệu"** đều là **near-miss** (gần chủ đề corpus) và mỗi case có **bằng chứng vắng mặt** (từ khoá tìm, không có kết quả trong 24 tài liệu; một test chạy lại). [REPO docs/specs/evaluation-dataset-design.md:72-80]
- **Coverage matrix** được sinh tự động và có test so khớp với blueprint; nó kiểm các "chỉ số thống trị" (EN 50%, recall 17%, tài liệu lớn 25% ...). [REPO docs/specs/evaluation-dataset-design.md:127-133]
- **Tại sao:** đây là cách làm cho bộ câu hỏi **có thể bác bỏ** giả thuyết thay vì chỉ minh hoạ.

### 3.4 Lược đồ hai file: ground truth tách khỏi kết quả
- Câu hỏi + ground truth nằm trong `data/evaluation/questions/`; kết quả sinh ra của **từng arm** nằm ở `data/evaluation/results/<run_id>/records.jsonl`, nối bằng `id`. Một bộ câu hỏi phục vụ hai arm mà không bị sửa. [REPO docs/specs/evaluation-dataset-design.md:121-125]
- **Xem một case thật** (chạy thử Python nhỏ đọc `eval-v1.jsonl`; case 13 là dòng thứ 13): `Q-EVAL-013` hỏi về middleware nhận scoped service qua constructor; có 3 answer point bắt buộc (P1 lỗi runtime vì scoped bị ép thành singleton, P2 inject vào `Invoke/InvokeAsync`, P3 dùng factory-based middleware), nguồn kỳ vọng `#10 Service lifetimes` (slot S1), **bốn** nguồn thay thế cùng slot, và hai mục `must_not_claim` (ví dụ "Register the service as a singleton to fix it."). [REPO data/evaluation/questions/eval-v1.jsonl:13-13]
- **Tại sao `must_not_claim`:** dùng cho kiểm **grounding/mâu thuẫn**: một câu trả lời chứa lời khuyên sai phổ biến bị `incorrect` dù có nhắc đúng các point khác.
- **Pitfalls `[GENERAL]`:** lưu kết quả của các arm vào **cùng một file** với ground truth sẽ làm hỏng freeze (hash đổi mỗi lần chạy).

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Vì sao bộ dev không bao giờ xuất hiện trong kết quả báo cáo?
<details><summary>Đáp án</summary>
Vì nó dùng để **chỉnh** prompt và luật "insufficient"; điểm trên dữ liệu đã dùng chỉnh là lạc quan giả (data leakage). Eval set giữ "chưa từng thấy" ([REPO docs/specs/evaluation-spec.md:25]).
</details>

**B2 (Basic).** Hệ thống nói "tài liệu không đủ" cho một câu **có** đáp án trong tài liệu. Nhãn nào? Có gọi judge không?
<details><summary>Đáp án</summary>
`false_refusal`, **không** cần judge (`map_result`: `answerable and insufficient`). [REPO src/knowledge_assistant/application/evaluation/metrics/mapping.py:60-61]
</details>

**B3 (Basic).** Tính MRR của ba câu: chunk trúng đầu tiên ở hạng 1, hạng 4, và không có.
<details><summary>Đáp án</summary>
`(1 + 0.25 + 0)/3 = 0.4167`. (Đơn vị `1/hạng` được kiểm ở mục E3: hạng 3 → 0.3333, không trúng → 0.0.)
</details>

**I1 (Intermediate).** Slot S1 = {#04 kỳ vọng}; slot S2 = {#26 kỳ vọng, #20 thay thế}. Top-5 chứa #04 và #20 (khoảng chồng lấn hợp lệ). Lenient và strict section hit là bao nhiêu? Slot fraction?
<details><summary>Đáp án</summary>
Lenient = 1 (cả S1, S2 thoả); strict = 0 (S2 không có nguồn kỳ vọng); `slot_fraction = 1.0` (lenient). Đúng kết quả mục E2 (`lenient sec 1 strict sec 0`, `fraction 1.0`). [REPO docs/specs/evaluation-spec.md:58]
</details>

**I2 (Intermediate).** Chunk giữ lại `C("12", 0, 30)` có bản trùng bị loại ở `("13", 0, 30)`; span kỳ vọng ở tài liệu 13 `[0,30)`. Section hit và source hit là bao nhiêu? Vì sao khác nhau?
<details><summary>Đáp án</summary>
Section = 1, source = 0 (mục E5). Section metric tính bản trùng (luật trùng lặp); source metric chỉ nhìn tài liệu của chunk được giữ, tức thứ người dùng thấy ([REPO src/knowledge_assistant/application/evaluation/metrics/retrieval.py:86-91]).
</details>

**I3 (Intermediate).** Có 31 câu answerable đã gắn nhãn: 22 `correct`, 5 `partially_correct`, 1 `incorrect`, 3 `false_refusal`. Tính `accuracy`, `lenient_accuracy`, `false_refusal_rate` và nêu mẫu số.
<details><summary>Đáp án</summary>
Mẫu số = 31 (answerable): `accuracy = 22/31 = 0.710`, `lenient = 27/31 = 0.871`, `false_refusal = 3/31 = 0.097`. (Các số này khớp phần "22/31" báo cáo ghi cho Arm A; tôi dựng bài tập này để khớp công thức, không phải để tái hiện phân bố nhãn thật — phân bố thật xem `summary.json`.) `[REPO src/knowledge_assistant/application/evaluation/scoring.py:225-231]`
</details>

**A1 (Advanced).** Có ba record: (a) corpus-insufficient, hệ thống từ chối trơn; (b) corpus-insufficient, hệ thống từ chối kèm `missing_information` "…chỉ nói về X"; (c) answerable, runner lỗi (không có câu trả lời). Mỗi record đi vào mẫu số nào và cần judge không?
<details><summary>Đáp án</summary>
(a) `correct_refusal`, unanswerable, **không** judge. (b) cần **refusal check**: `correct_refusal` nếu judge nói không trình bày nội dung liên quan như đáp án, `hallucination` nếu ngược lại; thuộc unanswerable (đa số từ chối do LLM tự viết đều có note nên đều đi đường này, spec dòng 67). (c) **không** thuộc mẫu số nào; được liệt kê trong `answer.runner_errors`. [REPO docs/specs/evaluation-spec.md:67], [REPO src/knowledge_assistant/application/evaluation/judge.py:95-103]
</details>

**A2 (Advanced).** Sửa **một khoảng trắng** trong một câu hỏi eval sau khi freeze. Điều gì xảy ra ở lượt chạy tiếp theo? Sửa thế nào cho đúng quy trình?
<details><summary>Đáp án</summary>
`verify_frozen_files` tính lại SHA-256, không khớp snapshot → `IntegrityError`, runner **từ chối chạy** (đã chạy thử mục E7). Cách đúng: không sửa im lặng; ghi **amendment** (cái gì, tại sao, ngày) và cập nhật snapshot/hash theo quy trình có duyệt của chủ dự án ([REPO src/knowledge_assistant/application/evaluation/integrity.py:36-39], [REPO docs/specs/evaluation-spec.md:87-88]).
</details>

**A3 (Advanced).** Bạn muốn báo cáo "Arm A tốt hơn Arm B vì accuracy 0.710 so với 0.742". Nêu ba lý do câu đó không được phép, dựa trên repo.
<details><summary>Đáp án</summary>
(1) B **cao hơn** A (0.742 > 0.710), nên câu phát biểu ngược số. (2) Hiệu `+0.032` có CI `[−0.097, 0.161]` chứa 0 và McNemar `b=2 c=3, p=1.0`: **không** khác biệt đáng tin ở n = 31. (3) "Wording rule": `p ≥ 0.05` báo là "không có khác biệt thống kê đáng tin tại n = X", không bao giờ là một arm "tốt hơn". [REPO docs/snapshots/experiments/exp-001.md:26], [REPO docs/reports/epics/EPIC-06-experiment.md:82-83]
</details>

## Self-check questions
1. Ground truth phải có trước cái gì? Vì sao?
2. Dev set và eval set khác nhau thế nào? Điều gì xảy ra nếu chỉnh trên eval?
3. Evidence slot là gì? Cho một ví dụ lenient trúng nhưng strict trượt.
4. Vì sao section hit dùng offset chứ không so heading?
5. Duplicate rule áp cho section hay source? Vì sao khác nhau?
6. Ba mẫu số là gì; record runner-error thuộc mẫu số nào?
7. Judge chọn nhãn hay `map_result` chọn?
8. Cơ chế nào làm cho việc sửa bộ câu hỏi im lặng bị phát hiện?

## Interview Q&A
1. **"Bạn thiết kế bộ đánh giá cho hệ thống RAG thế nào?"** — Ground truth viết trước index; tách dev/eval; đóng băng bằng hash + tag; metric tách tầng (retrieval, câu trả lời, citation, latency); có nhóm song song cho ngôn ngữ; near-miss cho từ chối ([REPO docs/specs/evaluation-dataset-design.md:9-13]).
2. **"Làm sao tránh tự lừa mình khi đánh giá?"** — Freeze + hash + amendment log; báo cả lenient và strict; báo `n` cho mọi tỉ lệ; liệt kê threats to validity; không chỉnh trên eval ([REPO docs/specs/evaluation-spec.md:87-98]).
3. **"Recall@k và MRR khác nhau ra sao?"** — hit@k: có tìm được trong k không; MRR: tìm được sớm cỡ nào (`1/hạng`). Repo báo hit@1/3/5 + MRR ([REPO src/knowledge_assistant/application/evaluation/metrics/retrieval.py:27]).
4. **"Vì sao không cho LLM chọn nhãn cuối?"** — Nhãn phải xác định và kiểm thử được; judge chỉ cấp dữ liệu, bảng `map_result` quyết định ([REPO src/knowledge_assistant/application/evaluation/metrics/mapping.py:1-4]).
5. **"Một metric có mẫu số sai thì sao?"** — Đã xảy ra: câu văn spec sai về mẫu số, sửa ở verify; báo cáo luôn ghi `22/31` vs `23/32` và lý do ([REPO docs/reports/epics/EPIC-06-experiment.md:80-81]).
6. **"Bạn báo cáo kết quả không có ý nghĩa thống kê thế nào?"** — "Không có khác biệt đáng tin ở n = X", kèm CI và số cặp bất đồng, không tuyên bố arm nào hơn ([REPO docs/reports/epics/EPIC-06-experiment.md:82-83]).

## Further reading
- Manning, Raghavan, Schütze, *Introduction to Information Retrieval* — chương đánh giá (precision/recall, MRR). `[GENERAL]`
- Es et al., *RAGAS: Automated Evaluation of Retrieval Augmented Generation* (arXiv:2309.15217) — bộ metric RAG phổ biến; so sánh với thiết kế thủ công ở đây. `[GENERAL]`
- Goodhart's law — bài Wikipedia cùng tên cho tổng quan ngắn. `[GENERAL]`
- Tiếp theo: [11](11-llm-as-judge.md) (judge), [12](12-statistics-for-experiments.md) (thống kê), [13](13-case-study-exp-001.md) (ca nghiên cứu tổng hợp).
