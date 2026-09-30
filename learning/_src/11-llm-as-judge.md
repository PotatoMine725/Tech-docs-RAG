# 11 · LLM-as-judge: prompt chấm điểm, judge chỉ cấp dữ liệu, parse chặt, cache, spot-check của người, Cohen's κ
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [08](08-generation-and-prompting.md), [09](09-llm-api-engineering.md), [10](10-evaluation-design.md) · Study time: ~8–10h · Home file của: LLM judge (answer check / refusal check), `judge_error`, parse verdict nghiêm ngặt, cache judgement + kiểm tra hợp lệ (prompt hash, model), self-preference bias, spot-check mù của chủ dự án, agreement & Cohen's κ
> Bài tập chạy được: `learning/_tools/exercises/judge_stats_scenarios.py` (mục J1–J4, S1; offline, không mạng, không key).

## Vì sao file này quan trọng trong dự án
Chấm 61 câu trả lời × nhiều point bằng tay là quá tốn công, nên dự án dùng **một LLM làm giám khảo (judge)**. Đó là con dao hai lưỡi: judge cũng có thể sai, cũng có thiên vị — và ở đây nó lại **chính là model đã viết câu trả lời** (`gemini-3.5-flash-lite`, ADR-0004 D12; [REPO docs/specs/evaluation-spec.md:69]). Cả phần thiết kế judge xoay quanh một câu hỏi: **làm sao dùng LLM chấm mà vẫn không tự lừa mình?** Câu trả lời của repo gồm bốn lớp: (1) judge chỉ cấp **dữ liệu**, luật gán nhãn là code (file 10 §2.6); (2) đầu ra judge được **parse cực nghiêm**, sai một chút là `judge_error`, không bao giờ đoán; (3) mọi judgement được **cache kèm hash prompt/model**; (4) một **con người** kiểm mù 10 verdict và ta đo mức đồng thuận bằng Cohen's κ.

---

## Level 1 — Basic

### 1.1 Judge là gì và vì sao cần
- **Ý tưởng:** *LLM-as-judge* = dùng một LLM để chấm đầu ra của LLM khác (hoặc của chính nó) theo một **rubric** (bảng tiêu chí) cho trước. Nó rẻ và nhanh, nhưng **không phải chân lý**: nó có thể dễ dãi, bị thuyết phục bởi văn phong, ưu ái câu trả lời giống phong cách của mình (*self-preference*).
- **C# analogy:** giống một bộ **test oracle tự động** — nhưng oracle này là xác suất, nên bạn phải kiểm chính oracle (spot-check) chứ không tin mù.
- **Trong repo này:** một lời gọi judge cho mỗi câu trả lời cần chấm; **không** dùng judge cho case mà bảng ánh xạ đã đủ để gán nhãn:
@@SNIP src/knowledge_assistant/application/evaluation/judge.py 95-103@@
- **Đọc chậm:** ba nhánh trả về: `None` (không gọi), `ANSWER_CHECK`, `REFUSAL_CHECK`. Câu **có đáp án và đã trả lời** → kiểm câu trả lời; câu **không có đáp án** mà hệ thống từ chối *trơn* → không gọi (đã rõ là `correct_refusal`); mọi ca còn lại của nhóm không-có-đáp-án → kiểm từ chối. Đã chạy thử offline (mục J3): 6 ca → `answer`, `None`, `None`, `refusal`, `refusal`, `None` (retrieval mode).
- **Tại sao:** ít lời gọi hơn = ít quota hơn, và **ít chỗ cho judge sai**. [REPO src/knowledge_assistant/application/evaluation/judge.py:1-13]
- **Pitfalls `[GENERAL]`:** dùng LLM chấm những thứ code kiểm được (ví dụ "câu trả lời có `[n]` không") là lãng phí và kém tin cậy hơn code.

### 1.2 Hai kiểu kiểm tra: "answer check" và "refusal check"
- **Answer check** (câu có đáp án, đã trả lời): với **mỗi required point** (theo `id`) judge nói `yes`/`partial`/`no`; có mâu thuẫn ground truth (kể cả `must_not_claim`) không; liệt kê **claim không được hỗ trợ**; với **mỗi citation marker** nói passage có hỗ trợ claim gắn với marker không; kèm `reason` ≤ 2 câu.
- **Refusal check** (câu không có đáp án): một boolean `presents_related_as_answer` + `reason`. Được coi là `true` nếu: trình bày nội dung liên quan như đáp án, trình bày một kỹ thuật *suy diễn* như điều tài liệu nói, đưa ra claim trả lời câu hỏi (dù đúng hay sai), hoặc **không nói** tài liệu không đủ.
- **Trong prompt:** rubric của answer check nằm ở đây (các mục 1–5), và nó bắt đầu bằng luật quan trọng nhất — "Do not use your own knowledge":
@@SNIP config/prompts/judge_v1.md 1-11@@
  Luật từ chối (sau `<!-- section: refusal -->`):
@@SNIP config/prompts/judge_v1.md 40-47@@
- **Tại sao "Judge ONLY against the GROUND TRUTH and the CITED PASSAGES":** một câu đúng theo kiến thức chung nhưng **không có trong tài liệu** phải bị tính là *unsupported* — mục tiêu là **grounded**, không phải "đúng ngoài đời".
- **Tại sao cho phép dịch/diễn đạt lại:** câu hỏi tiếng Việt có câu trả lời tiếng Việt trong khi ground truth tiếng Anh; judge phải so **nghĩa**, không so chữ.
- **Pitfalls `[GENERAL]`:** ví dụ *few-shot* trong prompt refusal ("made up": mã hoá hàng đợi tin nhắn) có thể **kéo lệch** judge; repo ghi rõ đó là ví dụ bịa để khỏi rò rỉ nội dung corpus.

### 1.3 Judge chỉ cấp **dữ liệu**; code chọn nhãn
- **Nhắc lại:** `map_result` ánh xạ `JudgeVerdict` → nhãn (file 10 §2.6). Judge **không bao giờ** tự nói "correct". Đã chạy thử offline (mục J1): 8 tổ hợp cho 8 nhãn kỳ vọng — ví dụ `("yes","partial")` → `partially_correct`; mọi point `yes` nhưng `contradicts_ground_truth=True` → `incorrect`; answerable mà thiếu verdict → `JudgeVerdictMissing`. [REPO src/knowledge_assistant/application/evaluation/metrics/mapping.py:50-71]
- **Points-covered** = `(yes + 0.5·partial)/số point`: `["yes","partial","no"]` → `0.5`; `["yes","yes"]` → `1.0` (mục J2). [REPO src/knowledge_assistant/application/evaluation/metrics/mapping.py:79-89]
- **Tại sao:** nếu để judge tự chọn nhãn thì "hôm nay `partially_correct`, mai `correct`" sẽ là nhiễu không kiểm soát được; tách nhãn ra code làm cho phần LLM chỉ còn là **đọc hiểu có cấu trúc**.

---

## Level 2 — Intermediate

### 2.1 Ghép prompt judge: input lấy từ **record**, không đọc lại file
- **Ý tưởng:** judge cần: câu hỏi, ground truth (điểm, biến thể chấp nhận, `must_not_claim`, tiêu chí citation), **câu trả lời**, `missing_information`, và **toàn văn** từng chunk được trích. Toàn văn chunk lấy từ danh sách `retrieved` **trong chính record** (không đọc lại từ file/DB), để judge thấy đúng thứ hệ thống đã thấy khi trả lời. [REPO src/knowledge_assistant/application/evaluation/judge.py:12-13]
@@SNIP src/knowledge_assistant/application/evaluation/judge.py 167-183@@
- **Đọc chậm:** một `dict` các giá trị + `_PLACEHOLDER.sub(lambda ..., templates[check])` — **cùng kỹ thuật một lượt regex** như prompt trả lời (file 08 §2.1), nên `{...}` trong câu trả lời/passages không bị coi là placeholder. Giá trị rỗng thay bằng `"(none)"`/`"(empty)"` để prompt luôn đầy đủ.
- **`parse_template`** tách file prompt thành hai section bằng marker `<!-- section: answerable|refusal -->` và **kiểm placeholder** của từng section (thiếu → `ValueError`). [REPO src/knowledge_assistant/application/evaluation/judge.py:128-141]
- **Tại sao một file hai section:** một prompt, một hash, một version cho cả hai kiểu kiểm tra; đổi một chữ là đổi version.
- **Pitfalls:** `[GENERAL]` đưa `expected_answer` vào prompt judge làm **judge thấy đáp án** — cần thiết ở đây (so với ground truth), nhưng nghĩa là judge **không mù** như một người chấm độc lập.

### 2.2 Parse **nghiêm ngặt**: sai một chút là `judge_error`
- **Ý tưởng:** đầu ra judge là JSON theo schema, nhưng schema **chưa đủ**: kiểm thêm rằng judge chấm **đúng tập point và đúng tập marker** của record này. Bất kỳ sai lệch nào → ném `JudgeOutputError`, bản ghi thành `judge_error`, **không đoán**.
@@SNIP src/knowledge_assistant/application/evaluation/judge.py 195-217@@
@@SNIP src/knowledge_assistant/application/evaluation/judge.py 218-228@@
- **Đọc chậm:**
  - `type(data.get("presents_related_as_answer")) is bool` (chứ không `isinstance`): chỉ chấp nhận đúng `True`/`False`; `1`, `"true"` hay `null` bị loại. (Lưu ý `isinstance(1, bool)` là `False` nhưng `isinstance(True, int)` là `True`, nên với **số nguyên** người ta phải dùng `type(m) is int` để loại `True`, xem dòng marker bên dưới.)
  - `sorted(map(str, got_ids)) == sorted(required_ids) and len(set(got_ids)) == len(got_ids)`: so **tập** id (không phân biệt thứ tự) và cấm trùng id. **Optional point bị liệt kê cũng là lỗi** (rubric bảo "do not list them").
  - `all(type(m) is int ...)` cho marker: `True` (là `int` trong Python) bị loại.
- **Đã chạy thử offline** (mục J4): JSON đúng → OK `['yes','partial']`; marker `22` thay vì `1` → `JudgeOutputError: citation markers [22] are not exactly [1]`; liệt kê thêm optional `P3` → lỗi; `covered:"maybe"` → lỗi; `marker: True` → lỗi.
- **Sự cố `[REAL]` (EVAL-004a):** 2/61 lời gọi judge lỗi, cả hai trên `Q-EVAL-002:B` — judge chép **mã nguồn `22`** vào trường marker trong khi câu trả lời chỉ có một citation, marker `1`. Chạy lại một lần (temperature 0) cho **cùng** lỗi; hai dòng đều được giữ, case bị **loại khỏi mọi mẫu số có nhãn** và được liệt kê tên. Verifier dựng lại prompt offline và xác nhận giả thuyết. [REPO docs/reports/epics/EPIC-05-evaluation.md:428-432], [REPO docs/reports/epics/EPIC-06-experiment.md:103-105]
- **C# analogy:** giống việc deserialize DTO rồi chạy `Validator` — chấp nhận "gần đúng" sẽ làm hỏng số liệu ở phía sau.
- **Tại sao:** thà thiếu một nhãn (và ghi rõ) còn hơn một nhãn **đoán** lẫn vào tỉ lệ; số `n` của mọi tỉ lệ vẫn trung thực.
- **Pitfalls `[GENERAL]`:** "sửa" JSON lỗi bằng regex/heuristic (ví dụ ép `22`→`1`) là *fabricating a verdict*. Dự án cấm bịa kết quả (CLAUDE.md rule 9).

### 2.3 Cache judgement và **kiểm tra hợp lệ** (validity checks)
- **Khoá cache:** `(case_id, arm, sha256(answer), judge_prompt_version)` — cùng một câu trả lời, cùng prompt → **không gọi lại** (tiết kiệm quota; xác định).
- **Dòng `judge_error` được thử lại** ở lần chạy sau; dòng `ok` thì không. Nhưng có một **chốt chặn**: nếu một dòng `ok` cùng khoá mà **khác hash prompt hoặc khác model** → `JudgeCacheMismatch`, **từ chối chạy** — không dùng lại, không ghi đè thầm lặng:
@@SNIP src/knowledge_assistant/application/evaluation/judge.py 308-320@@
- **Đọc chậm:** vòng `for key, entry in latest.items()` với `continue` bỏ qua khoá khác version/khác trạng thái; vế `raise JudgeCacheMismatch(...)` ghi rõ cách xử lý ("Bump the prompt version or use another run folder; judgements are never mixed or overwritten").
- **Model purity:** một judgement từ model **khác** model judge được cấu hình, hoặc từ **fallback**, bị từ chối thành `judge_error` (`JudgeModelMismatch`). [REPO src/knowledge_assistant/application/evaluation/judge.py:394-399] Judge cố định `temperature 0` và **không có fallback**; thông số này **không cấu hình được**. [REPO src/knowledge_assistant/config.py:160-162]
- **Tại sao:** nếu prompt thay đổi mà vẫn dùng verdict cũ thì bạn đang chấm bằng **hai rubric khác nhau** mà không biết. Hash làm cho việc đó **không thể xảy ra im lặng**.
- **C# analogy:** memoization với khoá gồm cả "phiên bản logic" — như cache HTTP có `ETag`.
- **Pitfalls `[GENERAL]`:** khoá cache chỉ theo nội dung câu trả lời mà không theo phiên bản prompt/model là nguồn gây kết quả "trộn" trong nghiên cứu.

### 2.4 Chạy resumable, có ngân sách, và **một dòng mỗi lần thử**
- **Vòng chạy** `JudgeRecords.run`: với mỗi record cần judge — bỏ qua nếu cache `ok`; dừng nếu chạm `--max-llm-calls`; gọi judge; **ghi ngay** dòng judgement (`append_judgement`); nếu lỗi quota thì **ghi rồi dừng** để chạy tiếp lần sau. Ngân sách đếm cả retry và fallback (`retry_count + 1 + int(fallback_used)`). [REPO src/knowledge_assistant/application/evaluation/judge.py:329-356]
- **Judge là bước riêng, chạy sau generation và không đồng thời với runner** (chung 500 RPD của model). [REPO docs/specs/evaluation-spec.md:66]
- **Tại sao ghi ngay từng dòng:** giống journaling — nếu tiến trình chết giữa chừng, những gì đã chấm không mất (xem file 04 về append-only/idempotent).
- **Pitfalls `[REAL]`:** lượt thật dùng **122 lời gọi LLM** (61 answer + 61 judge, gồm một lần resume) và **0** lỗi 429/5xx. [REPO docs/reports/epics/EPIC-05-evaluation.md:433-435]

---

## Level 3 — Advanced

### 3.1 Thiên vị của judge: self-preference và cách repo đối phó
- **Vấn đề:** judge = model viết câu trả lời (`gemini-3.5-flash-lite`). Nghiên cứu cộng đồng cho thấy LLM có xu hướng chấm cao văn bản giống của mình `[GENERAL]`. Repo **ghi nhận là giới hạn**, không giấu. [REPO docs/specs/evaluation-spec.md:69]
- **Biện pháp đã có (đều nhằm giảm/kiểm soát, không loại bỏ):**
  1. Judge chỉ nhìn **ground truth + passages đã trích**, cấm dùng kiến thức riêng.
  2. Nhãn do code quyết định, không do judge.
  3. Parse nghiêm ngặt + cache hash.
  4. **Spot-check mù của con người** (3.2).
- **Biện pháp chưa có `[GENERAL]`:** dùng một model *khác* để chấm; chấm nhiều lần lấy đa số; hiệu chỉnh vị trí/độ dài. Repo không làm (quota, phạm vi) — đây là hướng mở rộng (file 16).
- **Tại sao quan trọng:** kết quả accuracy ở file 13 phụ thuộc judge; hiểu giới hạn này để không nói quá.

### 3.2 Spot-check mù của chủ dự án và Cohen's κ
- **Thiết kế:** lấy mẫu **10** verdict (seed 42, phân tầng) trên 59 verdict; tạo **tờ mù** (không có id case, arm, nhãn judge) cho chủ dự án chấm từng point; một **file khoá** riêng chứa verdict của judge. Script chấm **từ chối chạy** nếu còn ô trống hoặc tờ và khoá lệch nhau. [REPO scripts/evaluation/score_spot_check.py:1-25]
- **Nhãn của người không gõ tay:** lấy điểm từng point của chủ dự án đưa qua **cùng `map_result`** → nhãn "phía người" được suy ra bằng đúng luật đã gán nhãn cho judge (so sánh công bằng, tái lập được). Cột "đồng ý với judge?" (tự khai, tổng thể) chỉ là dòng phụ vì nó **bỏ qua** `map_result`. [REPO scripts/evaluation/score_spot_check.py:13-19]
- **Kết quả thật:** agreement dựa trên luật **8/10 = 0.800**, Cohen's κ **0.688**; tự khai tổng thể **9/10**. Hai bất đồng làm đổi nhãn (S09, S10): chủ dự án chấm một point `yes` còn judge chấm `partial`, nên nhãn nhảy `partially_correct`→`correct`. Một bất đồng nữa (S03) chỉ ở mức point, không đổi nhãn. n = 10/59 nhỏ; **một** mục đổi làm tỉ lệ dịch 10 điểm %. [REPO docs/reports/epics/EPIC-05-evaluation.md:375-397], [REPO docs/reports/epics/EPIC-05-evaluation.md:436-438]
- **Xu hướng quan sát được:** ở cả hai bất đồng làm đổi nhãn, judge **khắt khe hơn** người (chấm `partial` chỗ người chấm `yes`). Đó là bằng chứng *ngược* với lo ngại "judge dễ dãi" trong mẫu 10 này — nhưng với n = 10 không thể khái quát. `[UNVERIFIED]` cho bất kỳ suy luận rộng hơn.
- **Cohen's κ là gì:** agreement thô `p_o` bị thổi phồng khi vài nhãn chiếm đa số. κ **trừ đi phần trùng do ngẫu nhiên** `p_e`: `κ = (p_o − p_e)/(1 − p_e)`.
@@SNIP scripts/evaluation/score_spot_check.py 191-204@@
- **Tự tay tái tạo (đã chạy thử, mục S1):** từ ma trận nhầm lẫn của báo cáo (judge \ chủ dự án): `correct` 4 (khớp), `correct_refusal` 2 (khớp), `partially_correct` → owner `correct` 2, `partially_correct` khớp 2. Đếm biên: judge `{correct 4, correct_refusal 2, partially_correct 4}` → `{.4,.2,.4}`; người `{correct 6, correct_refusal 2, partially_correct 2}` → `{.6,.2,.2}`. `p_o = 0.8`, `p_e = .4×.6 + .2×.2 + .4×.2 = 0.36`, `κ = (0.8−0.36)/(1−0.36) = 0.6875 ≈ 0.688`. Hàm trả `0.688` khớp báo cáo.
- **Ca biên trong code:** danh sách rỗng → `None`; một nhãn duy nhất khớp hoàn toàn (`p_e ≥ 1`) → `1.0` ("không có ngẫu nhiên để hiệu chỉnh"). Đã chạy thử: `cohens_kappa([("a","a")]*5) = 1.0`, `cohens_kappa([]) = None`.
- **Đọc κ thế nào:** `[GENERAL]` thang Landis–Koch xếp 0.61–0.80 là "đồng thuận đáng kể (substantial)". Đây chỉ là quy ước tham khảo; với n = 10 khoảng tin cậy của κ rất rộng.
- **C# analogy:** giống việc so hai bộ test-runner: không chỉ hỏi "trùng bao nhiêu %" mà "trùng nhiều hơn so với việc tung xúc xắc theo cùng tần suất nhãn".
- **Pitfalls `[REAL]`:** báo cáo thực thi ban đầu ghi "9/10 đồng ý" (câu trả lời tự khai của chủ dự án). Verifier tính lại từ **điểm từng point mù** của chính chủ dự án qua `map_result` ra **8/10**; báo cáo và ledger được sửa để nêu **cả hai** số. Bài học: luôn ưu tiên con số **tái tạo được bằng máy** làm headline. [REPO docs/reports/epics/EPIC-05-evaluation.md:436-438]

### 3.3 Thiết kế prompt judge: điều cần để ý khi tự viết
Đọc `judge_v1.md` như một mẫu:
- **Ràng buộc nguồn kiến thức** ("Judge ONLY against ...") — chặn judge "biết thêm".
- **Liệt kê bắt buộc theo id** — ép judge chấm *từng* point và *từng* marker (dễ kiểm bằng code, xem 2.2).
- **Ba mức `yes/partial/no`** thay vì điểm số liên tục — ít nhiễu hơn, ánh xạ dễ sang nhãn.
- **`reason` ≤ 2 câu** — đủ để kiểm tra bằng mắt, không làm phình output.
- **Ngôn ngữ:** cho phép dịch — vì bộ eval song ngữ.
- **Pitfalls `[GENERAL]`:** rubric càng phức tạp, judge càng dễ lỗi định dạng (xem `Q-EVAL-002:B`); giữ schema nhỏ và kiểm chặt phía code.

### 3.4 Judge trong toàn bộ pipeline đánh giá
Sơ đồ tóm tắt:
1. **Runner** sinh record cho từng case × arm (file 10 §3.4; `run_evaluation.py`).
2. **Judge** đọc record, gọi LLM (chỉ khi `judge_check` ≠ None), ghi `judgements.jsonl`.
3. **Scoring** (`scoring.py`) nối record + judgement + spans → hàng điểm; `summarize` tính tỉ lệ với mẫu số đúng. [REPO src/knowledge_assistant/application/evaluation/scoring.py:158-179]
4. **Spot-check** kiểm mẫu nhỏ độ tin cậy của judge.
5. **So sánh hai arm** bằng thống kê ghép cặp (file 12).
- **Tại sao tách bước:** mỗi bước chạy **độc lập, resumable, kiểm được**; sửa một tầng không phải chạy lại tầng trước.

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Vì sao câu hỏi *không có đáp án* mà hệ thống từ chối "trơn" không cần gọi judge?
<details><summary>Đáp án</summary>
Không có gì cần chấm: hệ thống nói "không đủ" và **không** kèm note/citation nào có thể bị coi là đáp án, nên `map_result` cho `correct_refusal` trực tiếp. Đã chạy thử: `judge_check(...)` = `None` (mục J3) và `map_result(answerable=False, insufficient=True)` = `correct_refusal` (mục J1). [REPO src/knowledge_assistant/application/evaluation/judge.py:95-103]
</details>

**B2 (Basic).** `points_covered(["yes","partial","no","yes"])`?
<details><summary>Đáp án</summary>
`(2 + 0.5×1)/4 = 0.625`. (Hàm cùng công thức: `["yes","partial","no"]` → `0.5`, mục J2.) [REPO src/knowledge_assistant/application/evaluation/metrics/mapping.py:79-89]
</details>

**B3 (Basic).** Judge trả `"covered": "maybe"`. Điều gì xảy ra với record?
<details><summary>Đáp án</summary>
`JudgeOutputError("a 'covered' value is not yes/partial/no")` → judgement `judge_error`, record **chưa gắn nhãn** (không đoán), được liệt kê riêng và bị loại khỏi các metric phụ thuộc judge. Đã chạy thử (mục J4). [REPO src/knowledge_assistant/application/evaluation/judge.py:217]
</details>

**I1 (Intermediate).** Record có hai required point `P1`,`P2` và một optional `P3`. Judge liệt kê cả ba. Kết quả? Vì sao quy tắc này hợp lý?
<details><summary>Đáp án</summary>
`JudgeOutputError: required point ids ['P1','P2','P3'] are not exactly ['P1','P2']` (mục J4). Rubric bảo "do not list" optional; nếu cho phép thì optional `no` có thể vô tình bị tính vào hạ điểm — tập id phải **khớp đúng** để phép ghép verdict ↔ ground truth không mơ hồ.
</details>

**I2 (Intermediate).** Bạn đổi một chữ trong `judge_v1.md` nhưng **không** đổi tên version và chạy lại judge trong run folder cũ. Điều gì xảy ra?
<details><summary>Đáp án</summary>
Hash prompt khác với `judge_prompt_sha256` của các dòng `ok` cùng khoá → `JudgeCacheMismatch`, judge **từ chối chạy**, thông báo yêu cầu "bump the prompt version or use another run folder". [REPO src/knowledge_assistant/application/evaluation/judge.py:308-320]
</details>

**I3 (Intermediate).** Tự tính κ cho 10 cặp: judge/người = `(A,A)×5, (B,B)×2, (A,B)×3`. Có bao nhiêu nhãn? `p_o`, `p_e`, `κ`?
<details><summary>Đáp án</summary>
`p_o = 7/10 = 0.7`. Judge: A=8, B=2 → `{.8,.2}`; người: A=5, B=5 → `{.5,.5}`. `p_e = .8×.5 + .2×.5 = 0.5`; `κ = (0.7−0.5)/(1−0.5) = 0.4`. (Kiểm bằng `cohens_kappa` với danh sách này; công thức kiểm bằng ma trận thật ở mục S1 cho `0.688`.) [REPO scripts/evaluation/score_spot_check.py:191-204]
</details>

**A1 (Advanced).** Vì sao headline là "8/10 rule-based" chứ không phải "9/10 holistic", dù 9 lớn hơn?
<details><summary>Đáp án</summary>
8/10 được **tái tạo bằng máy** từ điểm từng point mù của chủ dự án qua cùng `map_result`, nên kiểm chứng được; 9/10 là câu trả lời **tự khai** tổng thể, bỏ qua `map_result` và có thể mâu thuẫn với điểm point của chính người đó (S09, S10). Chọn số tái tạo được là chọn số **khó bị tự lừa** ([REPO scripts/evaluation/score_spot_check.py:13-19], [REPO docs/reports/epics/EPIC-05-evaluation.md:436-438]).
</details>

**A2 (Advanced).** Thiết kế một kiểm tra `[GENERAL]` để phát hiện *self-preference* mà không cần model khác. Nêu giả thuyết và cách đo.
<details><summary>Đáp án</summary>
Ví dụ: lấy vài câu trả lời đúng/sai đã biết (do người gán), **xáo trộn thứ tự/độ dài/phong cách** (diễn đạt lại bằng cách khác) rồi để judge chấm; nếu điểm thay đổi theo phong cách chứ không theo nội dung → có thiên vị hình thức. Hoặc so tỉ lệ đồng thuận với người **riêng** cho câu trả lời do model này viết vs do model khác viết. Đây là ý tưởng `[GENERAL]`, repo **không** thực hiện; giới hạn được ghi nhận ở [REPO docs/specs/evaluation-spec.md:69].
</details>

**A3 (Advanced).** Vì sao ghi **từng dòng judgement ngay** thay vì gom cuối rồi ghi một lần? Nêu một lợi ích và một rủi ro của cách ghi từng dòng.
<details><summary>Đáp án</summary>
Lợi ích: chịu được gián đoạn (quota, mất điện) — kết quả đã có không mất, resume bỏ qua khoá `ok`; đồng thời có **lịch sử** (dòng lỗi + dòng thử lại cùng tồn tại). Rủi ro: cần quy ước "dòng cuối cùng thắng" (`latest_judgements`) và có thể có nhiều dòng cho một khoá — người đọc file thô phải biết điều đó. [REPO src/knowledge_assistant/application/evaluation/judge.py:118-125]
</details>

## Self-check questions
1. Vì sao judge không được chọn nhãn cuối cùng?
2. `answer check` và `refusal check` khác nhau ở đâu và khi nào dùng?
3. Parse verdict kiểm những gì ngoài schema? Vì sao?
4. Khoá cache gồm gì? Hash prompt để làm gì?
5. Self-preference là gì và repo ghi nhận nó ở đâu?
6. Cohen's κ khác agreement thô ở điểm nào?
7. Vì sao 8/10 là headline chứ không phải 9/10?

## Interview Q&A
1. **"Bạn dùng LLM-as-judge thế nào cho đáng tin?"** — Rubric ràng buộc nguồn; judge chỉ cấp dữ liệu, nhãn do code; parse nghiêm ngặt; cache khoá hash; spot-check mù bằng người + κ ([REPO src/knowledge_assistant/application/evaluation/judge.py:1-30]).
2. **"Judge và model trả lời là một — có vấn đề gì?"** — Self-preference; repo ghi nhận giới hạn và bù bằng spot-check, không tuyên bố loại bỏ được ([REPO docs/specs/evaluation-spec.md:69]).
3. **"Judge trả JSON sai thì làm gì?"** — `judge_error`, giữ raw text, thử lại một lần, rồi liệt kê record như chưa gắn nhãn; **không** đoán ([REPO src/knowledge_assistant/application/evaluation/judge.py:195-228]).
4. **"Cohen's κ dùng để làm gì?"** — Đo đồng thuận đã hiệu chỉnh cho ngẫu nhiên; ở đây 0.688 với 8/10 ([REPO docs/reports/epics/EPIC-05-evaluation.md:375-383]).
5. **"Bạn đổi prompt judge giữa chừng thì sao?"** — Hash khác → `JudgeCacheMismatch`; phải tăng version hoặc dùng thư mục mới ([REPO src/knowledge_assistant/application/evaluation/judge.py:308-320]).
6. **"Kể một lỗi thật của judge."** — `Q-EVAL-002:B`: judge chép source id `22` vào trường marker; parse chặt bắt được; record chưa gắn nhãn, được liệt kê ([REPO docs/reports/epics/EPIC-06-experiment.md:103-105]).

## Further reading
- Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* (arXiv:2306.05685) — bài nền tảng về LLM-as-judge và các thiên vị (vị trí, độ dài, self-enhancement). `[GENERAL]`
- Cohen, J. (1960), *A coefficient of agreement for nominal scales* — bài gốc của κ. `[GENERAL]`
- Landis & Koch (1977) — thang diễn giải κ. `[GENERAL]`
- Tiếp theo: [12](12-statistics-for-experiments.md) (thống kê ghép cặp) và [13](13-case-study-exp-001.md) (ca nghiên cứu).
