# 08 · Sinh câu trả lời và prompt: template có phiên bản, structured output, luật từ chối, phân tích citation, prompt injection
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [01](01-python-for-csharp-devs.md), [01b](01b-python-code-reading-guide.md), [05](05-rag-fundamentals.md), [09](09-llm-api-engineering.md) · Study time: ~8–10h · Home file của: prompt template & phiên bản (`answer_v1`→`v2`), ghép prompt bằng một lượt regex, JSON-mode structured output, schema + kiểm kiểu, hai lớp "insufficient" (phần LLM), marker `[n]`, `resolve_citations`, `count_uncited_sentences`, excerpt, prompt injection
> Bài tập chạy được: `learning/_tools/exercises/generation_scenarios.py` (offline, không mạng, không key).

## Vì sao file này quan trọng trong dự án
Đây là đoạn code quyết định câu trả lời có **đáng tin** hay không. Dự án có hai cam kết: (1) mọi câu trả lời phải dựa trên các passage đã truy xuất, kèm citation trỏ về đúng heading; (2) nếu tài liệu không đủ thì phải **nói rõ là không đủ** chứ không được bịa ([REPO CLAUDE.md:10]). Hai cam kết đó được hiện thực bằng ba thứ nhỏ: một file prompt có phiên bản, một schema JSON ép model trả về đúng dạng, và một bộ hàm thuần (pure function) đọc lại `[1]`, `[2]` trong câu trả lời để dựng citation. Phần lớn "kỹ thuật prompt" ở đây thực ra là **kỹ thuật phần mềm**: kiểm kiểu đầu ra, không tin model, và test được offline.

---

## Level 1 — Basic

### 1.1 Prompt là một file có phiên bản, không nằm trong code
- **Ý tưởng:** nội dung prompt là **dữ liệu cấu hình**. Tên file chính là phiên bản (`answer_v2`), và phiên bản được ghi vào mọi kết quả (`AnswerResult.prompt_version`) để về sau biết một câu trả lời sinh từ prompt nào.
- **C# analogy:** giống file `.resx`/template Razor tách khỏi code, hoặc `appsettings.json` — nhưng ở đây còn *bất biến theo phiên bản*: sửa prompt nghĩa là tạo file mới, không sửa file cũ.
- **Trong repo này:** toàn bộ prompt đang dùng:
@@SNIP config/prompts/answer_v2.md 1-15@@
  Ba placeholder: `{answer_language}`, `{passages}`, `{question}`. Các "luật" 1–6 là hợp đồng với model; nếu bạn đọc chậm, luật 2 là luật **từ chối** (xem 1.4).
- **Tại sao:** spec ghi "Prompts are never inlined in code. The file holds exactly the text sent" ([REPO docs/specs/generation-spec.md:20-21]). Nhờ vậy prompt diff được bằng Git, và bằng chứng đánh giá tham chiếu được đúng bản đã chạy.
- **Pitfalls `[REAL]`:** `answer_v1` đã dùng cho các câu trả lời live đầu tiên. Khi phát hiện lỗi (xem 2.3), repo **không sửa** `answer_v1.md` mà tạo `answer_v2.md` — khác đúng một câu ở luật 4 ("Wrap code, identifiers and expressions in backticks."). [REPO docs/specs/generation-spec.md:22-24]

### 1.2 Kiến trúc lời gọi: ai làm gì
`AnswerQuestion.ask` (tầng application) điều phối bốn việc; nó **không** biết Gemini là gì, chỉ biết interface `LLM`:

| Bước | Ai làm | Ghi chú |
|---|---|---|
| Phát hiện ngôn ngữ câu hỏi | `detect_language` | quyết định ngôn ngữ trả lời + thông báo "không đủ" (file 05) |
| Truy xuất + cổng ngưỡng | `Retriever`, so `score < threshold` | file 07 |
| Dựng prompt + gọi LLM | `PromptBuilder`, `LLM.generate` | file này + file 09 |
| Đọc JSON, dựng citation | `parse_answer_json`, `resolve_citations` | file này |

Toàn bộ `ask()`:
@@SNIP src/knowledge_assistant/application/generation/answer_question.py 76-96@@
Đọc chậm: `retrieved[0].score < self.threshold` là **cổng truy xuất** (lớp "insufficient" thứ nhất). Nếu cổng bật, hàm `return` ngay với `llm=None` — **không có lời gọi API nào**. Phần còn lại (từ dòng 98) chỉ chạy khi cổng mở:
@@SNIP src/knowledge_assistant/application/generation/answer_question.py 98-121@@
- **Đọc từng dòng:** dòng gọi `generate` truyền `response_schema=ANSWER_SCHEMA`; `parse_answer_json` kiểm kiểu; `resolve_citations` biến `[n]` thành đối tượng `Citation`; câu trả lời hiển thị là **thông báo địa phương hoá** nếu `insufficient` và là `answer` đã làm sạch nếu không. `**common` là *dict unpacking* (file 01b): gộp bốn trường dùng chung vào hai chỗ tạo `AnswerResult` mà không lặp code.
- **Tại sao `clock` là tham số:** `clock=time.perf_counter` mặc định, test truyền đồng hồ giả để độ trễ **xác định** (kỹ thuật dependency injection quen thuộc từ C#: `TimeProvider`).
- **Pitfalls:** `[GENERAL]` đừng gộp hai lớp "insufficient". Một cái là **điểm truy xuất thấp** (không tốn API), một cái là **model tự nói thiếu thông tin** (tốn 1 lời gọi). Chúng được phân biệt bằng `insufficient_reason` = `"retrieval_gate"` hoặc `"llm"` ([REPO src/knowledge_assistant/application/generation/answer_question.py:23-24]).

### 1.3 Structured output: bắt model trả JSON có schema
- **Ý tưởng:** thay vì để model viết văn tự do rồi "cào" chuỗi, ta yêu cầu **JSON mode** với một **JSON Schema**: model chỉ được sinh object có đúng bốn khoá. Gemini nhận schema qua `response_json_schema` (dict JSON Schema thuần); `response_mime_type="application/json"` bật chế độ JSON ([REPO src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py:179-181]).
- **Trong repo này:**
@@SNIP src/knowledge_assistant/application/generation/prompt_builder.py 13-26@@
  - `insufficient` (bool): model tự nhận là không đủ thông tin.
  - `answer` (string): câu trả lời, mỗi câu khẳng định kèm `[n]`.
  - `cited_passages` (list int): các số passage được dùng.
  - `missing_information` (string): phần tài liệu **không** nói tới.
- **C# analogy:** giống `System.Text.Json` với `record` + `[JsonRequired]`; hoặc "contract" của một API DTO. Khác biệt lớn: ở C# bạn deserialize và tin kiểu; ở đây model là **nguồn không đáng tin**, nên mọi kiểu đều phải kiểm lại (xem 1.5).
- **Tại sao `ANSWER_SCHEMA` nằm ở application còn adapter Gemini chỉ truyền dict:** để tầng core/infrastructure không cần biết schema là gì; adapter chỉ chuyển tiếp (`LLMRequest.response_schema`). [REPO src/knowledge_assistant/core/interfaces/llm.py:13-33]
- **Pitfalls:** `[GENERAL]` JSON mode **không đảm bảo ngữ nghĩa**: model vẫn có thể trả `"insufficient": false` với `answer` rỗng, hoặc `cited_passages` chứa số không tồn tại. Hai thứ đó được bắt ở 1.5 và 2.2.

### 1.4 Luật từ chối: "insufficient" là câu trả lời hợp lệ
- **Luật 2 của prompt** (văn bản của chủ dự án, `RAG-002 addendum 3`): nếu CONTEXT thiếu thông tin thì đặt `"insufficient": true`, để `answer` rỗng và ghi `missing_information`. Nếu chỉ thiếu một phần thì **trả lời phần có** và nêu phần thiếu. [REPO docs/specs/generation-spec.md:25-27]
- **Quyết định D2 (24/09/2026):** khi insufficient vẫn được giữ `missing_information` và có thể giữ các citation "liên quan" — nhưng nội dung liên quan **không được trình bày như câu trả lời**. [REPO docs/specs/generation-spec.md:12]
- **Hệ quả trong code:** khi `insufficient=True` thì `answer` hiển thị = thông báo cố định từ `config/messages.json` (đúng ngôn ngữ), **không** dùng chuỗi model sinh:
@@SNIP config/messages.json 1-6@@
  ([REPO src/knowledge_assistant/application/generation/answer_question.py:27-33] nạp file này và kiểm cả hai ngôn ngữ `en`, `vi` đều có.)
- **Tại sao:** một thông báo cố định thì **kiểm thử được** và không thể bịa; model chỉ quyết định *có/không*, không quyết định *lời lẽ*.
- **Pitfalls `[GENERAL]`:** một model an toàn quá mức sẽ từ chối cả những câu có đáp án (recall giảm), model dễ dãi sẽ bịa. Hai lớp (cổng ngưỡng + luật 2) tồn tại chính vì không lớp nào một mình đủ; đo cả hai ở file 10.

### 1.5 Không tin đầu ra của model: `parse_answer_json`
- **Ý tưởng:** trước khi dùng, kiểm **có phải JSON**, **có phải object**, **đủ bốn khoá**, **đúng kiểu từng khoá**, và **không phải "trả lời nhưng rỗng"**. Sai bất cứ điều gì → ném `GenerationError` kèm `raw_text` để chẩn đoán.
@@SNIP src/knowledge_assistant/application/generation/answer_question.py 36-56@@
- **Đọc chậm:**
  - `checks = {...}` là dict **khoá → hàm kiểm** (lambda). `wrong = [key for key, check in checks.items() if key not in data or not check(data[key])]` là *list comprehension* có điều kiện (file 01b).
  - `isinstance(n, int) and not isinstance(n, bool)`: trong Python `bool` **là** subclass của `int` (`True == 1`), nên `[true]` sẽ lọt qua kiểm `int` nếu không loại `bool` ra. Đây là chi tiết dễ quên.
  - `raise ... from error` giữ nguyên lỗi gốc (`__cause__`) — giống `throw new X(..., innerException)` trong C#.
- **Đã chạy thử offline** (`generation_scenarios.py`, mục C5): JSON hỏng → `GenerationError`; `[1]` (list, không phải object) → lỗi; thiếu khoá → lỗi nêu danh sách khoá sai; `cited_passages: [true]` → lỗi (nhờ loại `bool`); `insufficient=false` + `answer` toàn khoảng trắng → lỗi; `insufficient=true` + `answer=""` → **hợp lệ**.
- **Tại sao `GenerationError` không được đổi thành "insufficient":** đầu ra hỏng là **lỗi hệ thống**, không phải kết luận về tài liệu. Cố ý phân biệt (docstring đầu file: "neither is ever turned into 'insufficient'"). [REPO src/knowledge_assistant/application/generation/answer_question.py:7-8]
- **Pitfalls:** `[GENERAL]` đừng `try/except Exception: return "insufficient"` để "cho êm". Nó làm số liệu đánh giá đẹp giả và giấu bug.

---

## Level 2 — Intermediate

### 2.1 Ghép prompt bằng **một lượt regex**, không dùng `str.format`
- **Ý tưởng:** template chứa `{passages}`, mà passage lại là **văn bản tuỳ ý** (tài liệu kỹ thuật đầy `{}`: C#, JSON, f-string). Nếu dùng `template.format(...)` thì dấu `{}` trong passage/câu hỏi có thể gây `KeyError`, hoặc — tệ hơn — bị coi là placeholder. Cách của repo: **một lần** `re.sub` trên template; text đã chèn **không bao giờ bị quét lại**.
@@SNIP src/knowledge_assistant/application/generation/prompt_builder.py 48-55@@
- **Đọc chậm:** `_PLACEHOLDER.sub(lambda match: values[match.group(1)], template)` — với mỗi match, gọi lambda lấy `values[tên]`. Vì `sub` duyệt template **một lần từ trái sang phải** và không duyệt lại chuỗi thay thế, `"{question}"` nằm trong passage được giữ nguyên.
- **Đã chạy thử offline** (mục C4): passage chứa `Use {question} and {passages} literally.` và câu hỏi chứa `{answer_language}` → prompt cuối giữ **nguyên văn** cả hai chuỗi; chỉ placeholder của template được thay (`LANG=Vietnamese`).
- **C# analogy:** `Regex.Replace(template, pattern, m => values[m.Groups[1].Value])` — cùng một ý với `MatchEvaluator`. So sánh với `string.Format`/interpolation: những cái đó sẽ nổ nếu dữ liệu chứa `{0}`.
- **Tại sao:** đây cũng là một tuyến phòng thủ nhỏ trước **template injection**: dữ liệu không thể tự biến thành placeholder.
- **Pitfalls `[GENERAL]`:** trong Python `"...".format(**values)` hoặc f-string với dữ liệu ngoài là nguồn lỗi phổ biến; dùng `string.Template` cũng chỉ giải quyết được một phần vì `$`.

### 2.2 Đánh số passage và định dạng khối CONTEXT
- **Ý tưởng:** passage được đánh số **1..k theo thứ hạng** (rank), mỗi khối có dòng tiêu đề `[n] Tên tài liệu — heading path` rồi thân văn bản. Số `n` này là **khoá** liên kết prompt ↔ citation: model viết `[2]`, code tra `retrieved[2-1]`.
@@SNIP src/knowledge_assistant/application/generation/prompt_builder.py 37-45@@
- **Đọc:** `enumerate(retrieved, start=1)` (đếm từ 1, không phải 0); `passage_body(chunk).strip()` bỏ dòng heading lặp lại ở đầu `embed_text` vì tiêu đề đã hiện ở dòng `[n]`. [REPO src/knowledge_assistant/application/common/passage.py:7-13]
- **Tại sao đánh số từ 1:** người và model quen `[1]`; `[0]` sẽ bị coi là **không phải marker** (xem 2.3) — nên số 0 an toàn cho việc "không phải citation".
- **Pitfalls:** `[GENERAL]` nếu thứ tự passage trong prompt khác thứ tự dùng để dựng citation, citation sẽ **trỏ nhầm** mà không lỗi nào báo. Repo dùng chung tuple `retrieved` cho cả hai (dòng `render_passages(retrieved)` và `resolve_citations(..., retrieved)`).

### 2.3 Marker `[n]` và sự cố `[REAL]` "chỉ mục mảng"
- **Ý tưởng:** citation trong văn bản là `[n]` (hoặc `[2][3]`). Đọc lại bằng regex `\[(\d+)\]`. Nhưng tài liệu là **tài liệu lập trình**: `args[0]`, `items[1]` trong code trông y hệt marker.
- **Sự cố `[REAL]` (RAG-002 fix F1, 26/09/2026):** verifier chạy thử một câu trả lời có `args[0]` và thấy code bị coi là citation. Quyết định của chủ dự án: `[n]` **trong inline code hoặc fenced block, và `[0]` ở bất cứ đâu, không phải marker** — để nguyên từng byte, không được ghi vào citation, không vào `dropped_markers`. Đồng thời tạo `answer_v2` yêu cầu model bọc code trong backtick để phân biệt. [REPO AI_WORKLOG.md:344-351], [REPO docs/specs/citation-spec.md:21-24]
- **Trong code — các regex:**
@@SNIP src/knowledge_assistant/application/citation/citations.py 16-22@@
  - `_MARKER = \[(\d+)\]`: khớp `[` + số + `]`, nhóm 1 là số.
  - `_SENTENCE_END`: kết thúc câu là `.`/`!`/`?` (kèm marker ngay sau) theo sau bởi khoảng trắng hoặc hết chuỗi, **hoặc** xuống dòng.
  - `_INLINE_CODE`: dùng **lookbehind/lookahead** `(?<!`)` và `(?!`)` để khớp một dãy backtick *chính xác* bằng độ dài, đóng bằng dãy cùng độ dài (`\1` là back-reference). Chi tiết regex xem 01b §T12.
- **Đã chạy thử offline** (mục C1): `"A is x. [1] B is y [2][1]."` → `[1, 2]` (thứ tự xuất hiện đầu tiên, **không lặp**); `` "Use `args[0]` here [2]." `` → `[2]` (marker trong code bị bỏ); một fenced block chứa `x[1]` rồi `Done [1]` → `[1]`; `"zero [0] and [3]"` → `[3]`.
- **Tại sao thiết kế dựa trên vị trí (offset) code span:** `_code_spans` quét từng dòng tìm fence mở/đóng (ký tự và độ dài fence phải khớp; fence không đóng chạy tới hết văn bản), rồi tìm inline code ở phần còn lại. `_is_marker` chỉ hỏi "n ≥ 1 và offset này không nằm trong span code nào?". [REPO src/knowledge_assistant/application/citation/citations.py:26-55]
- **Pitfalls:** `[GENERAL]` viết regex "một dòng" cho Markdown luôn sai ở ca biên (fence lồng, backtick kép). Repo giải bằng cách **lập danh sách vùng code trước** rồi mới lọc marker.

### 2.4 `resolve_citations`: từ marker đến đối tượng `Citation`
@@SNIP src/knowledge_assistant/application/citation/citations.py 136-150@@
- **Đọc chậm:**
  - `dict.fromkeys(extract_markers(answer) + list(cited_passages))` — nối hai danh sách rồi **khử trùng lặp giữ thứ tự** (dict giữ thứ tự chèn; file 01b). Marker trong văn bản được ưu tiên trước, sau đó tới số chỉ có trong `cited_passages`.
  - Số ngoài `1..k` (`k = len(retrieved)`) → **`dropped`**: bị xoá khỏi văn bản (`remove_markers`) và ghi lại; model bịa `[7]` khi chỉ có 5 passage sẽ không tạo citation ma.
  - `retrieved[n - 1]` đổi số 1-based thành index 0-based.
- **Đã chạy thử offline** (mục C2, hai passage): `"A holds [1]. B holds [2]."` + `[1,2]` → giữ nguyên, marker `[1,2]`; `"A holds [1] [5]."` + `[1]` → `"A holds [1]."`, `dropped=(5,)`; `"No markers here."` + `[2]` → citation `[2]` vẫn có (từ `cited_passages`); `"A [1]."` + `[1,7]` → `dropped=(7,)`.
- **Citation gồm gì:** `source_id`, tên tài liệu, `location` = heading path nối bằng `HEADING_PATH_SEPARATOR`, `excerpt`, `chunk_id`, `marker`, URL nguồn, `location_type="heading"`. Không có số trang (CLAUDE.md rule 5). [REPO src/knowledge_assistant/application/citation/citations.py:122-133]
- **C# analogy:** một hàm thuần `(string, IList<int>, IReadOnlyList<Chunk>) -> (string, IReadOnlyList<Citation>, IReadOnlyList<int>)`; trả về tuple ba phần (Python cho phép, C# dùng `ValueTuple`).
- **Tại sao trả `dropped` thay vì ném lỗi:** model hay sai số; đây là dữ liệu **chẩn đoán** (chất lượng model), không phải lý do làm hỏng lượt hỏi.

### 2.5 `excerpt`: đoạn trích phải *tìm lại được* trong chunk
- **Ý tưởng:** citation hiển thị tối đa 300 ký tự đầu của passage, cắt về **ranh giới từ** cuối cùng, **không thêm "…"** — vì đó là **tiền tố nguyên văn** của chunk nên có thể `in` lại để kiểm.
@@SNIP src/knowledge_assistant/application/citation/citations.py 74-85@@
- **Đã chạy thử offline** (mục C6): `excerpt("word " * 100, 12)` → `'word word'` (12 ký tự đầu là `word word wo`, cắt lùi về khoảng trắng cuối); chuỗi ngắn giữ nguyên.
- **Tại sao:** validation/đánh giá có thể chứng minh "excerpt là văn bản thật của tài liệu" — nền tảng của tính **grounded**. Nếu thêm dấu `…` thì phép kiểm chứng tiền tố hỏng.
- **Pitfalls:** `[GENERAL]` cắt theo ký tự có thể cắt giữa từ/giữa surrogate; ở đây tài liệu tiếng Anh nên cắt theo khoảng trắng là đủ, nhưng với văn bản CJK cần cách khác.

### 2.6 Chẩn đoán: `count_uncited_sentences`
- **Ý tưởng:** luật 3 của prompt yêu cầu mọi câu khẳng định sự kiện có `[n]`. Hàm này **đếm** các câu có từ 5 từ trở lên mà không có marker thật — đây là **chỉ số chẩn đoán**, không chặn câu trả lời.
@@SNIP src/knowledge_assistant/application/citation/citations.py 110-119@@
- **Đọc chậm:** `_mask_non_markers` thay `[` của `[n]` không hợp lệ (trong code, `[0]`) bằng ký tự `\x00` **cùng độ dài** để `_MARKER.search` chỉ thấy marker thật; `len(_WORD.findall(_MARKER.sub("", sentence))) >= MIN_WORDS_FOR_FACT` đếm từ sau khi bỏ marker.
- **Đã chạy thử offline** (mục C3): `"This sentence has five words. [1]"` → 0; cùng câu không marker → 1; `"Short one. This sentence has five words though [2]."` → 0 (câu ngắn 2 từ **không** bị đếm, câu dài có marker); `` "Use `a[1]` in this sentence please." `` → **1** (marker duy nhất nằm trong code nên câu vẫn "không có trích dẫn").
- **Tại sao chỉ chẩn đoán:** đếm câu bằng regex chỉ là xấp xỉ; biến nó thành cổng chặn sẽ tạo dương tính giả. Nó chỉ được ghi vào `AnswerResult.uncited_sentences` để báo cáo.
- **Pitfalls `[GENERAL]`:** "mọi câu đều có marker" **không** chứng minh câu trả lời đúng; nó chỉ nói model *tuân thủ định dạng*. Tính đúng phải đo bằng đánh giá (file 10, 11).

---

## Level 3 — Advanced

### 3.1 Từ prompt v1 sang v2: quy trình thay đổi có kiểm soát
- **Câu chuyện thật:** `answer_v1` được chủ dự án duyệt (2 lời gọi live); luật 2 là văn bản của chủ dự án; hai bổ sung nhỏ ở luật 3 và 4 được **trình rồi duyệt** ([REPO AI_WORKLOG.md:329]). Sau đó fix F1 thêm câu "Wrap code…" thành `answer_v2`; `answer_v1.md` **giữ nguyên** vì các câu trả lời live đầu tiên được sinh bằng nó. [REPO docs/specs/generation-spec.md:22-24]
- **Bài học kỹ thuật:**
  1. Prompt là **artifact có version**; đổi = file mới + cập nhật `ANSWER_PROMPT_VERSION` trong cấu hình (không sửa code).
  2. Thay đổi được **kiểm chứng bằng mutation**: tắt phần bỏ qua code → 7 test fail; tắt luật `[0]` → 3 test fail; tổng test tăng 369 → 384 (+15). [REPO AI_WORKLOG.md:351-352]
  3. Prompt và code parser **ràng buộc nhau** (prompt bảo bọc backtick ↔ parser bỏ qua backtick). Đổi một bên mà quên bên kia là lỗi im lặng.
- **Tại sao `load_template` kiểm placeholder:** `missing = [p for p in PLACEHOLDERS if p not in template]` rồi `raise ValueError` — một template thiếu `{passages}` sẽ **chạy được nhưng không có ngữ cảnh**, tức model trả lời từ trí nhớ. Lỗi được chặn ngay lúc nạp. [REPO src/knowledge_assistant/application/generation/prompt_builder.py:29-34]

### 3.2 Temperature 0, giới hạn output, và tính tái lập
- **Cấu hình quyết định:** `temperature = 0.0`, `max_output_tokens = 1024` cho model chính; model dự phòng có ngân sách riêng 2048 vì có "thinking" (file 09). [REPO docs/specs/generation-spec.md:30-32]
- **Đọc adapter:** `options = {"temperature": request.temperature, "max_output_tokens": max_output_tokens}` rồi bổ sung `response_mime_type`/`response_json_schema` khi có schema. [REPO src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py:179-181]
- **Tại sao temperature 0:** giảm phương sai để so sánh hai arm (A/B) công bằng. Nhưng `[GENERAL]` temperature 0 **không đảm bảo** kết quả giống hệt (thứ tự tính toán song song, cập nhật model phía server). Vì vậy repo ghim **tên model chính xác** (không `-latest`, file 09 §1.2) và ghi `model_used` trên từng câu trả lời.
- **Pitfalls `[UNVERIFIED]`:** repo chưa có bằng chứng live về việc hai lần chạy cùng câu hỏi có cho JSON giống hệt hay không; không nên khẳng định "xác định tuyệt đối".

### 3.3 Prompt injection: rủi ro mà đồ án **cố ý không phòng thủ**
- **Ý tưởng:** *prompt injection* là khi văn bản trong dữ liệu (ở đây là passage) chứa lệnh nhắm vào model ("bỏ qua hướng dẫn trước…"). Trong RAG, **mọi passage là input không đáng tin** trừ khi bạn kiểm soát kho.
- **Trong repo này — sự thật thẳng thắn:** README nói rõ rủi ro này là của **phần mở rộng tương lai** (cho phép người dùng nạp tài liệu): "which this project's fixed, curated, read-only corpus never had to defend against". [REPO README.md:323-325] Không có bộ lọc injection nào trong `prompt_builder.py`. Cái repo *có* là: corpus cố định, được tuyển chọn thủ công (CLAUDE.md rule 4), và đầu ra được **ép qua schema + kiểm kiểu** nên một passage độc hại khó chuyển thành hành động ngoài JSON đó.
- **Tại sao vẫn nên học:** khi tài liệu do người dùng cung cấp, bạn cần: tách rõ dữ liệu và chỉ dẫn (dùng khối CONTEXT có ranh giới), không cho model **quyền hành động** (ở đây model chỉ trả JSON), kiểm đầu ra, và ghi log. Mẫu "một lượt regex" ở 2.1 chặn một lớp tấn công *template*, **không** chặn injection *ngữ nghĩa*.
- **Pitfalls `[GENERAL]`:** không có prompt nào "chống injection 100%". OWASP xếp prompt injection là rủi ro hàng đầu cho ứng dụng LLM; xem Further reading. Phòng thủ nhiều lớp, đặc quyền tối thiểu.

### 3.4 Ai kiểm chứng câu trả lời "grounded"? Ranh giới của chương này
- Mọi thứ trong file này bảo đảm **hình thức** (đúng schema, citation trỏ tới passage tồn tại, excerpt là văn bản thật). Nó **không** chứng minh câu trả lời **đúng nghĩa** so với passage. Việc đó do **đánh giá** đảm nhiệm: hit rule (file 10) và LLM judge (file 11) với spot-check của con người.
- **Tại sao phân tách:** nếu code sinh câu trả lời tự chấm chính nó thì mọi con số đều đáng ngờ; CLAUDE.md rule 9: "MUST NOT fabricate results". [REPO CLAUDE.md:13]

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Prompt v2 khác v1 ở đâu, và vì sao repo giữ cả hai file?
<details><summary>Đáp án</summary>
Chỉ khác luật 4: v2 thêm "Wrap code, identifiers and expressions in backticks." (đã kiểm bằng `diff` hai file). Giữ v1 vì các câu trả lời live đầu tiên được sinh bằng nó; sửa tại chỗ sẽ làm bằng chứng cũ không còn khớp file ([REPO docs/specs/generation-spec.md:22-24]).
</details>

**B2 (Basic).** Cổng truy xuất bật thì `AnswerResult.llm` là gì và `insufficient_reason` là gì? Có lời gọi API nào không?
<details><summary>Đáp án</summary>
`llm=None`, `insufficient_reason="retrieval_gate"`, **không** có lời gọi API ([REPO src/knowledge_assistant/application/generation/answer_question.py:90-96]).
</details>

**B3 (Basic).** Vì sao `parse_answer_json` loại `bool` khỏi kiểm `int` trong `cited_passages`?
<details><summary>Đáp án</summary>
Vì `bool` là subclass của `int` trong Python: `isinstance(True, int)` là `True`, nên `[true]` sẽ lọt qua. Đã chạy thử: `cited_passages: [true]` → `GenerationError` ([REPO src/knowledge_assistant/application/generation/answer_question.py:47-48]).
</details>

**I1 (Intermediate).** Dự đoán `extract_markers` với: (a) `"See [2] and [2][1]."`, (b) `` "`x[3]` and [4]" ``, (c) `"[0][1]"`. Rồi chạy `generation_scenarios.py` mục C1 để kiểm cách đọc `[0]` và code.
<details><summary>Đáp án</summary>
(a) `[2, 1]` — thứ tự xuất hiện đầu tiên, khử lặp. (b) `[4]` — `[3]` nằm trong backtick nên không phải marker. (c) `[1]` — `[0]` không bao giờ là marker. (Mục C1 đã chạy các ca tương tự: `[1,2]`, `[2]`, `[1]`, `[3]`; (a)–(c) suy ra từ cùng quy tắc `_is_marker` ở [REPO src/knowledge_assistant/application/citation/citations.py:53-55].)
</details>

**I2 (Intermediate).** Có 3 passage. Model trả `answer="X is true [2]. Y is true [9]."`, `cited_passages=[2, 3]`. `resolve_citations` trả gì?
<details><summary>Đáp án</summary>
`order = [2, 9, 3]` (marker `[2]`,`[9]` rồi `cited_passages` `[2,3]`, khử lặp giữ thứ tự) → `dropped=(9,)`, `kept=[2,3]`; văn bản được làm sạch thành `"X is true [2]. Y is true."` (`remove_markers` xoá cả khoảng trắng trước `[9]`); citations có marker `2` rồi `3`. Cùng cơ chế với ca `"A holds [1] [5]."` đã chạy trong C2 ([REPO src/knowledge_assistant/application/citation/citations.py:145-150]).
</details>

**I3 (Intermediate).** Viết (giấy) một test chứng minh `build_prompt` không "thực thi" dấu `{}` trong dữ liệu. Cần dữ liệu và khẳng định gì?
<details><summary>Đáp án</summary>
Template dùng ba placeholder thật; passage chứa `{question}` và `{passages}` nguyên văn, câu hỏi chứa `{answer_language}`. Khẳng định: chuỗi trả về chứa **đúng nguyên văn** cả ba chuỗi đó một lần mỗi nơi, và `LANG=Vietnamese` chỉ xuất hiện ở chỗ placeholder của template. Đây chính là mục C4 (đã chạy) — kết quả `Use {question} and {passages} literally.` và `Q: What is {answer_language}?` ([REPO src/knowledge_assistant/application/generation/prompt_builder.py:48-55]).
</details>

**A1 (Advanced).** Vì sao `GenerationError` (JSON hỏng) không được chuyển thành `insufficient=True`, dù kết quả cho người dùng "trông giống" nhau?
<details><summary>Đáp án</summary>
Vì hai điều khác nghĩa: "tài liệu không đủ" là **kết luận về dữ liệu**; "đầu ra hỏng" là **lỗi hệ thống**. Gộp lại sẽ (1) che bug prompt/schema, (2) làm tỉ lệ từ chối bị thổi phồng hoặc thấp giả trong đánh giá, (3) khiến người dùng tin rằng tài liệu thiếu khi thực ra chỉ cần thử lại. Docstring và spec ghi rõ ([REPO src/knowledge_assistant/application/generation/answer_question.py:7-8], [REPO docs/specs/generation-spec.md:36-38]).
</details>

**A2 (Advanced).** Model trả `insufficient=true` nhưng `cited_passages=[1]` và `missing_information="…"`. Người dùng thấy gì?
<details><summary>Đáp án</summary>
`answer` = thông báo cố định trong đúng ngôn ngữ; `missing_information` được giữ; `citations` = các passage liên quan (quyết định D2), với `uncited_sentences=0`. Nội dung liên quan **không** được trình bày như câu trả lời ([REPO src/knowledge_assistant/application/generation/answer_question.py:110-121], [REPO docs/specs/generation-spec.md:12]). Mục C5 xác nhận `insufficient=true` + `answer=""` là JSON hợp lệ.
</details>

**A3 (Advanced).** Thiết kế mở rộng cho **người dùng nạp tài liệu** (upload). Nêu ba rủi ro về prompt và một biện pháp cho mỗi rủi ro.
<details><summary>Đáp án</summary>
(1) *Prompt injection* trong tài liệu → giữ ranh giới CONTEXT rõ ràng, model không có công cụ/hành động, kiểm đầu ra bằng schema (đã có), thêm bộ lọc/ghi log; README liệt kê đây là rủi ro của bản mở rộng ([REPO README.md:323-325]). (2) *Rò rỉ giữa người dùng* → index và cache tách theo người dùng (README:326-327). (3) *Không có ground truth* → chỉ kiểm được độ đúng của retrieval/citation, không kiểm được "đáp án đúng" (README:319-322). Mọi biện pháp mới ở đây là `[GENERAL]`, không phải hành vi hiện có của repo.
</details>

## Self-check questions
1. Hai lớp "insufficient" là gì, chúng khác nhau về chi phí API thế nào?
2. Vì sao dùng một lượt `re.sub` thay cho `str.format` khi ghép prompt?
3. `[0]` và `args[0]` có phải marker không? Vì sao?
4. `resolve_citations` làm gì với số nằm ngoài `1..k`?
5. Vì sao excerpt không có dấu `…`?
6. `count_uncited_sentences` có chặn câu trả lời không? Vì sao?
7. Prompt injection có được phòng thủ trong repo này không? Nói chính xác.

## Interview Q&A
1. **"Bạn ép LLM trả về dữ liệu có cấu trúc thế nào và tin nó tới đâu?"** — JSON mode + schema, **rồi kiểm lại kiểu ở phía mình**: JSON mode không đảm bảo ngữ nghĩa (`answer` rỗng, số passage ngoài phạm vi). Đầu ra hỏng ném `GenerationError` chứ không im lặng chấp nhận ([REPO src/knowledge_assistant/application/generation/answer_question.py:36-56]).
2. **"Bạn quản lý phiên bản prompt ra sao?"** — Prompt là file bất biến theo phiên bản, tên file là version, ghi vào từng kết quả; sửa = file mới, giữ bản cũ làm bằng chứng ([REPO docs/specs/generation-spec.md:20-24]).
3. **"Làm sao ngăn model bịa citation?"** — Đánh số passage; model chỉ được trích số 1..k; số ngoài phạm vi bị bỏ và ghi lại; excerpt là tiền tố nguyên văn nên kiểm được ([REPO src/knowledge_assistant/application/citation/citations.py:136-150]).
4. **"Kể một lỗi tương tác giữa prompt và parser."** — `args[0]` bị coi là citation; sửa cả hai phía: parser bỏ qua code, prompt v2 yêu cầu bọc backtick; kiểm bằng mutation (7 và 3 test fail khi tắt) ([REPO AI_WORKLOG.md:344-352]).
5. **"Bạn phân biệt 'không có câu trả lời' và 'hệ thống lỗi' thế nào?"** — Ba đường riêng: cổng truy xuất, `insufficient` của model (cả hai là kết quả hợp lệ), và `GenerationError`/`LLMError` (lỗi). Không bao giờ đổi lỗi thành insufficient ([REPO docs/specs/generation-spec.md:36-38]).
6. **"Prompt injection ảnh hưởng gì tới hệ thống này?"** — Corpus cố định nên hiện chưa phải rủi ro thực tế; repo nêu rõ đó là rủi ro của bản có upload và không có bộ lọc injection. Trả lời trung thực quan trọng hơn khoe phòng thủ không có ([REPO README.md:323-325]).

## Further reading
- Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (arXiv:2005.11401) — bài gốc về RAG. `[GENERAL]`
- OWASP, *Top 10 for Large Language Model Applications* (`https://owasp.org/www-project-top-10-for-large-language-model-applications/`) — mục về prompt injection. `[GENERAL]`
- Python docs, module `re` (`https://docs.python.org/3/library/re.html`) — `re.sub` với hàm, lookbehind/lookahead, back-reference. `[GENERAL]`
- JSON Schema (`https://json-schema.org`) — cú pháp schema dùng cho structured output. `[GENERAL]`
- Google AI for Developers: *Gemini API — Structured output* (tài liệu chính thức; tham số có thể đổi giữa các phiên bản SDK). `[GENERAL]`
- Tiếp theo: [09](09-llm-api-engineering.md) (gọi API bền vững) và 10 (thiết kế đánh giá).
