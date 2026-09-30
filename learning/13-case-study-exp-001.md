# 13 · Ca nghiên cứu EXP-001: Arm A vs Arm B từ giả thuyết đến kết luận trung thực
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [07](07-chunking-and-retrieval.md), [10](10-evaluation-design.md), [11](11-llm-as-judge.md), [12](12-statistics-for-experiments.md) · Study time: ~7–9h · Home file của: câu chuyện thí nghiệm hoàn chỉnh, biến được giữ hằng, kiểm soát bằng máy (refuse-to-run), failure analysis theo tầng, đọc từng ca bất đồng, lỗi phía đo lường (judge/gate), kết luận trung thực
> File này **không có khái niệm mới**: nó là nơi bạn dùng mọi thứ đã học. Số liệu lấy từ báo cáo/snapshot có trong repo tại commit ghim; **tôi không chạy lại thí nghiệm** (không gọi API, dữ liệu chunk nằm ngoài git). Bài tập chạy được: `learning/_tools/exercises/judge_stats_scenarios.py` (tái tạo các dòng thống kê của bảng).

## Vì sao file này quan trọng trong dự án
Đề bài có hai phần "ăn điểm" là thí nghiệm ≥ 2 hướng tiếp cận và phân tích lỗi có bằng chứng ([REPO CLAUDE.md:5], [REPO docs/specs/evaluation-spec.md:10]). EXP-001 là câu trả lời đầy đủ: **một** biến thay đổi (bộ chunker), mọi thứ khác được giữ hằng, cùng một bộ câu hỏi đóng băng, kiểm định ghép cặp, đọc từng ca bất đồng ở tầng chunk, và kết luận nói đúng mức dữ liệu cho phép. Đọc file này như đọc một bản mẫu của **một báo cáo thí nghiệm ML/RAG nghiêm túc**. Toàn bộ EXP-001 tốn **0 request Gemini**: nó chỉ đọc các run đã commit. [REPO docs/snapshots/experiments/exp-001.md:17]

---

## Level 1 — Basic

### 1.1 Câu hỏi của thí nghiệm và vì sao chỉ đổi **một** thứ
- **Câu hỏi:** chunking "header-aware" (Arm A) có tốt hơn "fixed-size" (Arm B) không? Đây là quyết định ADR-0003 D7 (hai arm). [REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:49-53]
- **Chỉ đổi chunker** (ADR-0003 D7):
  | | Arm A | Arm B |
  |---|---|---|
  | Chunker | header-aware `header-1600`: tách theo H2/H3, tối đa 1600, tối thiểu 400, code fence và bảng nguyên khối, overlap 200 chỉ khi tách section quá dài, bỏ chunk chỉ có heading | fixed-size `fixed-1600`: cửa sổ 1600 ký tự, overlap 200, **không** quan tâm heading hay code fence |
  | Số chunk | 733 (đã loại 447 chunk trùng nguyên văn) | 859 (không trùng) |
  [REPO docs/reports/epics/EPIC-06-experiment.md:27-31]
- **Tại sao chỉ một biến:** nếu đổi cả chunker lẫn prompt, bạn không biết cái nào gây ra khác biệt (confounding). Đây là **nguyên tắc nền tảng** của thí nghiệm có kiểm soát.
- **C# analogy:** A/B test một feature flag — mọi thứ khác (build, dữ liệu, tải) giữ nguyên.

### 1.2 Danh sách những gì giữ hằng
Cả hai run dùng: embedding `gemini-embedding-001`/768, khoảng cách cosine, top-k 5, over-fetch 10 (rồi dedup theo `passage_hash`), ngưỡng cổng 0.686, prompt `answer_v2`, model trả lời **và** judge `gemini-3.5-flash-lite`, **tắt fallback**, bộ câu hỏi `eval-v1` (tag `eval-freeze-v1`, 36 case), cùng commit code `491f137` với `git_dirty: false`. [REPO docs/snapshots/experiments/exp-001.md:8-17], [REPO docs/reports/epics/EPIC-06-experiment.md:33-46]
- **Đọc chậm:** đây là **danh sách kiểm** (control list). Mỗi dòng trả lời câu hỏi "biến nào khác có thể giải thích khác biệt?".
- **Tại sao `allow_fallback` nằm trong danh sách:** nếu một arm tình cờ dùng model dự phòng thì so sánh không còn công bằng (file 09 §2.4).
- **Pitfalls `[GENERAL]`:** liệt kê điều kiện giữ hằng **sau khi** thí nghiệm xong là sự tự lừa; ở đây danh sách được **máy kiểm** (1.3).

### 1.3 Kiểm soát bằng máy: "từ chối chạy nếu không công bằng"
- **Ý tưởng:** script so sánh không tin người dùng. Nó đọc cấu hình của **cả hai run** và **từ chối chạy** nếu bất kỳ thiết lập giữ-hằng nào khác nhau; và từ chối nếu file chunk không khớp hash đã ghi trong `summary.json`:
**`scripts/experiments/compare_arms.py:52-53`**
```python
HELD_CONSTANT = ("embedding_model", "embedding_dim", "top_k", "overfetch", "threshold", "prompt_version",
                 "prompt_sha256", "answer_model", "allow_fallback", "mode", "split", "freeze_tag", "question_files")
```
**`scripts/experiments/compare_arms.py:186-192`**
```python
        raise SystemExit(f"--run-a must be arm A and --run-b arm B, got {a['arm']} and {b['arm']}")
    config_a, config_b = a["run"]["config"], b["run"]["config"]
    differing = [key for key in HELD_CONSTANT if config_a.get(key) != config_b.get(key)]
    if differing:
        raise SystemExit(f"runs differ on held-constant settings: {differing}")
    if not sha256(SPANS) == a["summary"]["inputs"]["expected-spans-v1.json"] == b["summary"]["inputs"]["expected-spans-v1.json"]:
        raise SystemExit("expected-spans-v1.json differs from the one the summaries used")
```
- **Đọc chậm:** `differing = [key for key in HELD_CONSTANT if config_a.get(key) != config_b.get(key)]` là list comprehension; nếu không rỗng → `raise SystemExit(...)` (thoát với thông báo — kiểu "fail fast" của script CLI). Dòng cuối là một **chuỗi so sánh** `sha256(SPANS) == a[...] == b[...]` (file 01b): cả ba hash phải bằng nhau.
- **Tại sao:** biến "so sánh công bằng" thành **một ràng buộc kiểm được**, không phải lời hứa.
- **C# analogy:** giống guard clause `Guard.Against.…` ở đầu một hàm quan trọng.

### 1.4 Chạy hai lần, tính toán offline
- **Cách chạy:** EVAL-004a chạy đầy đủ hai arm trên bộ eval; EXP-001 **chỉ đọc** kết quả đã commit, tính bảng bằng `scripts/experiments/compare_arms.py` (xác định, offline, 0 request Gemini). [REPO scripts/experiments/compare_arms.py:1-16]
- **Caching và thứ tự chạy:** Arm A chạy trước và tính 36 embedding câu hỏi bằng API; Arm B dùng lại embedding từ cache SQLite (0 request embedding). Đây tiết kiệm quota (file 06 §cache) **nhưng** làm độ trễ `embed_query` của B nhỏ hơn một cách giả tạo (0.1 ms vs 352 ms). [REPO docs/reports/epics/EPIC-06-experiment.md:113-118]
- **Tại sao đáng học:** cache là **công cụ tiết kiệm** và đồng thời là **biến gây nhiễu**. Biết rõ nó ảnh hưởng số nào (độ trễ) và số nào không (hit@k) là kỹ năng đọc kết quả.

---

## Level 2 — Intermediate

### 2.1 Kết quả headline (Δ = B − A) và cách đọc từng dòng
Bảng (đã chạy thử để **tái tạo phần thống kê** ở file 12 §2.1):
| Metric | A | B | Δ | 95% CI | Test | p | n |
|---|---|---|---|---|---|---|---|
| section hit@5 | 0.938 | 0.938 | 0.000 | [−0.094, 0.094] | McNemar b=1 c=1 | 1.000 | 32 |
| evidence hit@1 | 0.594 | 0.406 | −0.188 | [−0.406, 0.062] | McNemar b=11 c=5 | 0.210 | 32 |
| evidence hit@5 | 0.938 | 0.844 | −0.094 | [−0.188, 0.000] | McNemar b=3 c=0 | 0.250 | 32 |
| accuracy | 0.710 | 0.742 | +0.032 | [−0.097, 0.161] | McNemar b=2 c=3 | 1.000 | 31 |
| lenient accuracy | 0.871 | 0.935 | +0.065 | [0.000, 0.161] | McNemar b=0 c=2 | 0.500 | 31 |
| false refusal | 0.129 | 0.065 | −0.065 | [−0.161, 0.000] | McNemar b=2 c=0 | 0.500 | 31 |
| prompt tokens/answer | 1628.6 | 2122.6 | +494.0 | [418.8, 567.2] | Wilcoxon | < 0.001 | 30 |
| chunk cắt code fence | 3.27% | 45.05% | — | — | mô tả | — | 733/859 |
[REPO docs/snapshots/experiments/exp-001.md:19-30]
- **Đọc chậm — bốn bài học ngay từ bảng:**
  1. **Hàng 1:** `section hit@5` bằng nhau 0.938 (mỗi bên 30/32), CI đối xứng quanh 0.
  2. **Hàng 2–3:** `evidence hit` **nghiêng về A** (0.594 vs 0.406 ở @1), nhưng `p = 0.21` — khác biệt **không đáng tin** ở n = 32 dù Δ = −0.188 trông lớn.
  3. **Hàng 4–6:** các số **answer-level** nghiêng về B (accuracy, false refusal) nhưng p = 1.0/0.5 — **không đáng tin**; ngay cả khi tất cả bất đồng nghiêng một phía (5 cặp) cũng chỉ p = 0.0625 (file 12 §2.2).
  4. **Hàng 7:** **chênh lệch đáng tin duy nhất** là chi phí: B gửi thêm ~494 prompt token mỗi câu (+30%).
- **Đã chạy thử offline** (file 12, mục S3): `mcnemar_exact` với (b, c) = (2, 3) → `1.0`; (11, 5) → `0.2101`; (1, 1) → `1.0` — khớp cột p.
- **Tại sao báo cả CI:** accuracy Δ = +0.032 với CI `[−0.097, +0.161]` nghĩa là dữ liệu tương thích với "mất ~10 điểm" đến "được ~16 điểm"; **không** chứng minh tương đương. [REPO docs/reports/epics/EPIC-06-experiment.md:575-577]
- **Pitfalls:** hai hàng cùng "A tốt hơn ở retrieval, B tốt hơn ở answer" **không** phải hai kết luận riêng: cả hai đều "không có khác biệt đáng tin". Đừng kể chuyện quá dữ liệu.

### 2.2 Vì sao hai arm giống nhau ở hit@5 nhưng khác ở hit@1 và token
Báo cáo giải thích bằng **dữ liệu chunk**, không bằng phỏng đoán: [REPO docs/reports/epics/EPIC-06-experiment.md:326-356]
1. **A giữ nguyên một section; B giữ láng giềng lại với nhau.** Chunk p50 của A là 1178 ký tự và bám heading; các chunk của B đều 1600 ký tự (p50 = p90), bắt đầu ở đâu cửa sổ rơi vào (giữa câu, giữa code, xuyên heading). Kết quả: khi đáp án nằm trong **một** section, chunk hạng 1 của A chứa đủ mọi point (11 ca chỉ A đúng: 005, 009, 010, 013, 015, 016, 018, 019, 021, 027, 031); khi đáp án trải qua **hai section ngắn liền kề** hoặc là tài liệu nhỏ (`#29`: A tách 3 chunk, B chỉ 1 chunk 1282 ký tự), B thắng (5 ca chỉ B: 003, 004, 011, 012, 023).
2. **Ở hạng 5 cả hai tìm cùng section:** một phần vì nhiều section đã gần 1600 ký tự (p90 của A = 1527), một phần vì cả hai nhúng cùng tiền tố heading-path (D5) — thứ mang phần lớn tín hiệu "đây là section nào".
3. **B tốn token hơn** vì năm cửa sổ 1600 ký tự dài hơn năm chunk p50 = 1178.
4. **B cắt code fence 14 lần nhiều hơn** (387/859 = 45.05% vs 24/733 = 3.27%): cơ chế đứng sau 018:B và 027:B. [REPO docs/reports/epics/EPIC-06-experiment.md:354-356]
- **Đọc chậm:** "**where in the top 5** the evidence lands and **how complete** each chunk is, more than whether it is retrieved" — câu tóm tắt cả thí nghiệm. [REPO docs/reports/epics/EPIC-06-experiment.md:349-350]
- **Tại sao đây là kỹ năng đáng học:** khi số liệu "không khác biệt", việc đào xuống mức chunk cho bạn biết **cơ chế**, nhờ đó quyết định tiếp theo có căn cứ.

### 2.3 Đọc từng ca bất đồng (discordant) — phương pháp
- **Định nghĩa:** 23 case khác nhau giữa hai arm ở nhãn, groundedness, hoặc bất kỳ retrieval metric nào. Với mỗi ca, báo cáo ghi "cái gì khác" và **giải thích ở mức chunk** (top-3 chunk mỗi arm, ID chunk, độ dài, điểm cổng…). [REPO docs/reports/epics/EPIC-06-experiment.md:358-388]
- **Bốn ca mẫu đáng đọc kỹ (mỗi ca dạy một điều):**
  - **001 — cổng, không phải chunker, quyết định.** Cùng section `#22 Querying Data` ở hạng 1 ở cả hai arm; chunk A dài 848 ký tự có điểm top-1 **0.6779 < 0.686** → cổng từ chối (`false_refusal`), chunk B (1600 ký tự đầu tài liệu) có **0.6908 ≥ 0.686** → trả lời đúng. Đây là ví dụ đẹp của **threat #1**: ngưỡng chỉnh trên A áp cho B. [REPO docs/reports/epics/EPIC-06-experiment.md:367]
  - **012 — thất bại ở generation, không phải retrieval.** A có mọi quote ngay trong top 2, nhưng câu trả lời bỏ sót point P2; chủ dự án chấm P2 là `no` (khắt khe hơn judge `partial`), nên nhãn **không** phải artefact của judge. [REPO docs/reports/epics/EPIC-06-experiment.md:373]
  - **022 — chunk gần trùng lấn át.** Hai slot (`...WithRedirects`, `...WithReExecute`). **Cả năm chunk của A** là các biến thể phiên bản của #13 chỉ thuộc slot S2; slot S1 không bao giờ vào ngữ cảnh → LLM từ chối. Cửa sổ của B nằm **vắt qua ranh giới** hai section nên cả hai slot đều được phủ → trả lời đúng. [REPO docs/reports/epics/EPIC-06-experiment.md:382]
  - **027 — cắt code và mất câu giải thích.** Chunk B hạng 1 bắt đầu giữa câu ("h an implementation that also supports…") và cắt một fence; câu P1 nằm ở cửa sổ **trước** đó (không được truy xuất) → câu trả lời thiếu `ValidationProblemDetails`. [REPO docs/reports/epics/EPIC-06-experiment.md:385]
- **C# analogy:** giống việc đọc từng test case fail trong một bộ regression thay vì chỉ nhìn tỉ lệ pass.
- **Tại sao:** từng ca chỉ ra **cơ chế cụ thể** mà không phép thử thống kê nào chỉ ra được. Đây là phần "failure analysis" được chấm điểm ([REPO docs/specs/evaluation-spec.md:10]).

### 2.4 Failure analysis theo **tầng**: máy phân loại, người đọc lại
- **Ý tưởng:** mỗi record thất bại được gán **một** tầng chính theo quy tắc **đầu tiên khớp**: `retrieval_miss` → (cổng) `refusal` → `chunking` → `ranking` → `refusal` (LLM) → `generation` → `citation`. Đây là một cây quyết định có thứ tự ưu tiên rõ ràng.
**`src/knowledge_assistant/application/evaluation/experiment.py:274-280`**
```python
def is_failure(row: dict) -> bool:
    """EXP-001 §2 trigger: result is not a success, or section hit@5 = 0. Unlabelled records are not classified."""
    result = (row["answer"] or {}).get("result")
    if result is None:
        return False
    miss = row["retrieval"] is not None and row["retrieval"]["section_hit@5"] == 0
    return result not in (CORRECT, CORRECT_REFUSAL) or miss
```
**`src/knowledge_assistant/application/evaluation/experiment.py:308-330`**
```python
    if retrieval is not None and retrieval["section_hit@5"] == 0:
        slots = retrieval.get("slot_fraction@5")
        return failure(RETRIEVAL_MISS, f"section_hit@5 = 0 (slot fraction {_fmt(slots)})")
    if result == FALSE_REFUSAL and record["gate_fired"]:
        return failure(REFUSAL, f"gate: top-1 score {record['top1_score']:.4f} < threshold {threshold}")
    hitting = [fact for fact in facts[:5] if fact.hits_section]
    if retrieval is not None and retrieval["evidence_hit@5"] == 0:
        return failure(CHUNKING, "section hit but evidence_hit@5 = 0 (no required-point quote whole in one chunk)")
    if len(hitting) == 1 and hitting[0].cuts_code_fence:
        return failure(CHUNKING, f"only section-hitting chunk {hitting[0].chunk_id} cuts a code fence")
    if hitting and hitting[0].rank >= 3:
        cited = {citation["chunk_id"] for citation in record["citations"]}
        wrong_above = [fact.chunk_id for fact in facts if fact.rank < hitting[0].rank and fact.chunk_id in cited
                       and not fact.hits_section]
        if wrong_above:
            return failure(RANKING, f"first section hit at rank {hitting[0].rank}; cites {wrong_above}")
    if result == FALSE_REFUSAL:
        return failure(REFUSAL, "LLM: answered insufficient although the gate passed")
    if result == HALLUCINATION:
        return failure(REFUSAL, "hallucination on a corpus-insufficient case")
    if result in (PARTIALLY_CORRECT, INCORRECT):
        return failure(GENERATION, f"{result}: expected section and evidence in context")
    return failure(CITATION, "correct answer with a citation defect")
```
- **Đọc chậm:** hàm nội `failure(stage, rule, extra=())` đóng gói việc tạo đối tượng và **lọc** thẻ phụ trùng tên tầng; `hitting = [fact for fact in facts[:5] if fact.hits_section]` chọn các chunk trong top 5 chạm section; các `if` sắp theo **thứ tự ưu tiên** nên một record chỉ vào một tầng.
- **Thứ tự quan trọng:** "gate refusal" đứng **trước** `chunking` vì khi cổng chặn, LLM **chưa bao giờ thấy chunk**, nên nguyên nhân là cổng chứ không phải chunk (owner addendum item 4). Tín hiệu chunking vẫn được giữ như thẻ phụ (016:B, 018:B). [REPO docs/reports/epics/EPIC-06-experiment.md:396-398]
- **Kết quả đếm** (mỗi arm tổng 9 lỗi): `retrieval_miss` A 2 / B 2; `chunking` A 0 / B 1; `ranking` 0 / 0; `refusal` A 3 / B 2; `generation` 4 / 4; `citation` 0 / 0. [REPO docs/reports/epics/EPIC-06-experiment.md:417-427]
- **Con người đọc lại:** "Tôi đọc cả 18 dòng lỗi so với dữ kiện chunk và không nhãn nào cần ghi đè" (`failure-overrides.json` là `{}`). [REPO docs/reports/epics/EPIC-06-experiment.md:413-415]
- **Hai phát hiện "bất ngờ tốt":** `ranking` **không bao giờ** kích hoạt; và `citation` **không thể** kích hoạt theo quy tắc trigger nên ba câu trả lời đúng có lỗi citation được liệt kê riêng (`citation_defects_on_correct_answers`). Báo cáo **tự nêu** giới hạn này thay vì giấu. [REPO docs/reports/epics/EPIC-06-experiment.md:405-411]
- **Tại sao phân tầng:** để quyết định "sửa ở đâu" (chunker, retriever, cổng, prompt, model). Nếu chỉ báo "18 lỗi", bạn không biết hành động tiếp theo.
- **Pitfalls `[GENERAL]`:** cây quy tắc có thứ tự tạo ra **định nghĩa**: chỉ đổi thứ tự là đổi kết quả. Vì vậy thứ tự phải được ghi và giải thích (đã có ở docstring dòng 284-295).

### 2.5 Đối chiếu với các failure mode ADR-0003 dự đoán
ADR đã **dự đoán** trước sáu chế độ lỗi; báo cáo trả lời từng cái là *có quan sát thấy không*: [REPO docs/reports/epics/EPIC-06-experiment.md:468-479]
| Dự đoán | Quan sát |
|---|---|
| Trộn phiên bản (#13/#17/#23) | **Retrieval có, câu trả lời không quan sát thấy** (top 5 đầy biến thể; judge không thấy mâu thuẫn) |
| Chunk gần trùng chiếm top-k | **Có** (022:A, 032:B) |
| Fixed-size tách code khỏi phần giải thích | **Có, ở Arm B** (45.05% vs 3.27%; 027:B, 018:B) |
| Nhiễu danh sách link (#08, #09) | **Không quan sát thấy** (0 chunk #08/#09 trong mọi top 5) |
| Tài liệu nhỏ thành một chunk | **Có, và nó giúp B** (011/012, 001) |
| Tài liệu lớn lấn át nhỏ | **Chỉ là nhiễu hạng thấp** |
- **Tại sao đây là điểm sáng:** một thí nghiệm tốt **có thể bác bỏ** dự đoán. Ở đây một số dự đoán "không xảy ra" (nhiễu link, trộn phiên bản ở câu trả lời) và báo cáo nói thẳng.

---

## Level 3 — Advanced

### 3.1 Lỗi phía **đo lường** (không phải lỗi hệ thống)
Phân biệt "hệ thống sai" với "cách đo sai" là một kỹ năng cấp cao. Báo cáo dành riêng một mục: [REPO docs/reports/epics/EPIC-06-experiment.md:534-554]
- **S03 (`Q-EVAL-012:A`):** judge khen một claim (P2) mà câu trả lời **không hề nói**; chủ dự án chấm `no`. Nhãn cuối vẫn `partially_correct` nên không số nào đổi, nhưng cho thấy **judge có thể rộng rãi ở mức point**.
- **`Q-EVAL-002:B`:** judge chép **mã nguồn `22`** (từ dòng "[1] #22 — Querying Data" trong prompt judge) vào trường marker → parse chặt từ chối hai lần → record chưa gắn nhãn (file 11 §2.2).
- **Groundedness khác biệt là artefact của judge:** ở 005:A judge liệt kê "avoid using the Task Parallel Library" là *unsupported* trong khi **chính `reason`** của nó kết thúc bằng "(wait, the table actually does say ... so the claim is supported)"; ở 026:A judge gắn cờ một link tải .NET 8 dù link đó **nằm trong chunk 3 A đã truy xuất**. Kết luận báo cáo: "groundedness as scored here says nothing reliable about the chunkers".
- **Hai khác biệt nhãn phụ thuộc vào một điểm point đơn lẻ:** 020 và 017:B (spot-check S09, S10).
- **Tại sao đáng học:** không có thống kê nào phát hiện được các lỗi này; chỉ **đọc từng ca ở mức bằng chứng** mới thấy. Nếu bỏ bước này, bạn sẽ gán "khác biệt" cho chunker trong khi nguyên nhân là judge hoặc ngưỡng.
- **Pitfalls `[GENERAL]`:** khi dùng LLM judge, luôn lấy mẫu vài ca bất đồng và **đọc `reason`** — nhiều lỗi lộ ra ở đó.

### 3.2 Kết luận trung thực: viết gì và **không** viết gì
Báo cáo kết luận như sau (tóm tắt, có ref): [REPO docs/reports/epics/EPIC-06-experiment.md:556-584]
- **Học được:** chọn chunker ít ảnh hưởng đến việc *tìm section* (cả hai đặt section kỳ vọng vào top 5 ở **30/32** ca) mà ảnh hưởng nhiều đến việc *một chunk chứa bao nhiêu đáp án*. **Không** có khác biệt answer-level đáng tin ở n = 31. Khác biệt đáng tin duy nhất là **token** (+30%).
- **Nhiều "khác biệt giữa hai arm" thực ra là hiệu ứng ngưỡng hoặc judge:** 001 (ngưỡng chỉnh trên A), 020 (một điểm point của judge), 005/026 (lỗi lập luận của judge). "Không đọc mức chunk thì chúng đã bị gán cho chunker."
- **Quyết định "nếu là tôi bây giờ"** (không áp dụng vì nhiệm vụ cấm đổi tham số; mọi thay đổi cần ADR): giữ **Arm A** làm mặc định vì **rẻ hơn** (−494 token), **giữ code nguyên** (3% vs 45%), citation **thẳng hàng với section**; coi ngưỡng cổng là **theo từng arm**; **không** dùng groundedness của judge này làm headline nếu chưa có người chấm thứ hai.
- **Không được viết:** "A tốt hơn B" hay "hai arm tương đương" — cả hai vượt quá dữ liệu (CI accuracy `[−0.097, +0.161]`, file 12 §3.2).
- **Tại sao đây là "đúng mức":** quyết định giữ A dựa trên **chi phí và cơ chế** (đo được và đáng tin), không dựa trên accuracy (không đáng tin).

### 3.3 Các thí nghiệm tiếp theo, mỗi cái kèm "metric nào cho thấy thành công"
1. **Hiệu chỉnh ngưỡng cổng theo từng arm** trên bộ dev ≥ 30 case/arm; thành công = `false_refusal` dưới 0.129 (A)/0.065 (B) trong khi `correct_refusal` vẫn 100%.
2. **Hybrid retrieval (BM25 + dense) với đa dạng hoá biến thể phiên bản** cho các tên API dạng từ vựng (`UseStatusCodePagesWithRedirects`, `IExceptionHandler`); thành công = các ca hai slot (017, 022, 030, 031, 032) đạt section hit@5 = 1 ở cả hai slot.
3. **Viết lại truy vấn VI→EN** trước truy xuất; thành công = khoảng cách VI−EN trên tập song song thu hẹp và các lỗi gắn thẻ `language` (010, 012:A) biến mất.
[REPO docs/reports/epics/EPIC-06-experiment.md:586-603]
- **Tại sao đây là mẫu tốt:** mỗi bước tiếp theo **gắn với metric thành công định trước** — đúng tinh thần "đóng băng trước, đo sau".
- **Liên hệ file 16:** đây là hạt giống của "beyond this project" (hybrid search, query rewriting, calibration).

### 3.4 Bài học quy trình: chuỗi "executor → verifier" đã bắt lỗi gì
- Báo cáo EXP-001 được **verifier độc lập** kiểm; các lỗi bắt được trong các vòng nối tiếp (một số ví dụ, đều có trong repo): số "9/10" tự khai vs "8/10" tái tạo bằng máy (file 11 §3.2); câu văn spec về mẫu số sai (file 10 §2.8); mốc thời gian index đầu tiên sai (ghi 14:55:42 trong khi thật là lần build đầu 09:12:06; sửa ở `ddeabb1`). [REPO docs/plans/task-ledger.md:35-35]
- **Tại sao:** một nhà nghiên cứu **không tự kiểm được** hết; chuỗi tác vụ chia vai (executor/verifier) là một dạng **peer review nội bộ**. Xem file 15 để biết cách nó được tổ chức.
- **Pitfalls `[UNVERIFIED]`:** dòng tóm tắt các lỗi verifier ở trên lấy từ ledger của repo; tôi không tái kiểm từng commit hash trong buổi này (danh sách hash nằm ở ledger, không phải tôi tự dựng).

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Liệt kê năm thứ **giữ hằng** giữa hai arm và một thứ **cố ý khác**.
<details><summary>Đáp án</summary>
Giữ hằng (5 trong số): embedding model/dimension, cosine, top-k 5 + over-fetch 10, ngưỡng 0.686, prompt `answer_v2`, model trả lời/judge, tắt fallback, bộ câu hỏi + hash, commit code. Cố ý khác: **chỉ chunker** (header-aware vs fixed-size). [REPO docs/reports/epics/EPIC-06-experiment.md:25-46]
</details>

**B2 (Basic).** Ở bảng headline, dòng nào là **chênh lệch đáng tin duy nhất** và vì sao?
<details><summary>Đáp án</summary>
`prompt tokens / answer`: Δ = +494.0, CI [418.8, 567.2] (không chứa 0), Wilcoxon `p < 0.001`, n = 30. Mọi dòng còn lại có `p ≥ 0.2` và/hoặc CI chứa 0. [REPO docs/snapshots/experiments/exp-001.md:19-30]
</details>

**B3 (Basic).** Vì sao "accuracy B 0.742 > A 0.710" không cho phép viết "B tốt hơn A"?
<details><summary>Đáp án</summary>
McNemar `b=2, c=3, p=1.0`; CI `[−0.097, 0.161]` chứa 0 → không có khác biệt đáng tin ở n = 31 (đã chạy thử: (2,3) → p=1.0, file 12 mục S3). Luật diễn đạt cấm nêu người thắng khi `p ≥ 0.05` ([REPO src/knowledge_assistant/application/evaluation/experiment.py:152-158]).
</details>

**I1 (Intermediate).** Ca 001: hai arm truy xuất **cùng section** ở hạng 1, nhưng A `false_refusal` còn B `correct`. Giải thích bằng số liệu và nói đó là lỗi tầng nào.
<details><summary>Đáp án</summary>
Chunk A (section 848 ký tự) có top-1 `0.6779 < 0.686` → cổng từ chối, LLM không thấy chunk; chunk B (1600 ký tự đầu tài liệu) có `0.6908 ≥ 0.686` → được trả lời. Tầng **`refusal` (gate)**, không phải chunking hay retrieval; và là biểu hiện của threat "ngưỡng chỉnh trên Arm A". Luật `score < threshold` là nghiêm ngặt (file 07 §3.3). [REPO docs/reports/epics/EPIC-06-experiment.md:367], [REPO docs/reports/epics/EPIC-06-experiment.md:87-91]
</details>

**I2 (Intermediate).** Tại sao "gate refusal" được đặt **trước** `chunking` trong cây phân loại?
<details><summary>Đáp án</summary>
Vì khi cổng chặn, LLM **chưa từng thấy chunk**: lỗi chunking không thể là nguyên nhân trực tiếp của từ chối. Nếu chunking đứng trước, 016:B và 018:B sẽ bị quy sai cho chunker; hiện chúng có tầng chính `refusal` và thẻ phụ `chunking`. [REPO src/knowledge_assistant/application/evaluation/experiment.py:311-312], [REPO docs/reports/epics/EPIC-06-experiment.md:396-398]
</details>

**I3 (Intermediate).** Báo cáo ghi accuracy Arm A là `22/31 = 0.710`, còn `summary.json` không ghép ghi `23/32 = 0.719`. Giải thích chênh lệch.
<details><summary>Đáp án</summary>
`Q-EVAL-002:A` **đúng** nhưng `Q-EVAL-002:B` chưa gắn nhãn (judge lỗi định dạng) nên case không có đối tác B → bị loại khỏi phép so **ghép cặp** (31 câu); `summary.json` đếm nó ở phía A (32 câu, 23 đúng). Đây là ví dụ mẫu số khác nhau giữa "ghép" và "không ghép" (file 10 §2.8). [REPO docs/reports/epics/EPIC-06-experiment.md:80-81]
</details>

**A1 (Advanced).** Bạn muốn kiểm chứng giả thuyết "B cắt code nhiều hơn nên B trả lời sai nhiều hơn". Dữ liệu nào ủng hộ và dữ liệu nào **không** cho phép kết luận?
<details><summary>Đáp án</summary>
Ủng hộ cơ chế: 45.05% vs 3.27% chunk cắt fence; hai ca cụ thể (027:B, 018:B) mà chunk cắt làm mất câu giải thích/point. **Không cho phép kết luận ở mức tập thể:** ở answer-level, accuracy khác biệt không đáng tin (p = 1.0), và chỉ một lỗi `chunking` (027:B); báo cáo viết "It did not produce a reliable answer-level difference at this n". Đó là **cơ chế có bằng chứng, hiệu ứng tập thể chưa chứng minh**. [REPO docs/reports/epics/EPIC-06-experiment.md:354-356]
</details>

**A2 (Advanced).** Vì sao độ trễ `embed_query` và `total` được **trình bày mà không kiểm định**, còn `retrieve` được kiểm định nhưng bị nói là "không đáng hành động"?
<details><summary>Đáp án</summary>
`embed_query`/`total` bị confounder: Arm A chạy trước và tính embedding live; Arm B toàn cache hit (`embed_query` p50 0.1 ms vs 352 ms) nên khác biệt là của **cache và thứ tự chạy**, không phải chunker. `retrieve` kiểm được nhưng chênh lệch tính bằng mili-giây và bị chi phối bởi truy vấn đầu tiên (cold start 414.6 ms), nên cũng không phải hiệu ứng chunker đáng hành động. [REPO docs/reports/epics/EPIC-06-experiment.md:113-118]
</details>

**A3 (Advanced).** Thiết kế thí nghiệm để tách **phương sai sinh câu trả lời của LLM** khỏi **hiệu ứng chunker** (hạn chế "một lần chạy mỗi arm").
<details><summary>Đáp án</summary>
Chạy mỗi arm **nhiều lần** (ví dụ 3–5) trên cùng bộ câu hỏi; với mỗi câu lấy tỉ lệ đúng qua các lần chạy; so **phương sai trong-arm** với chênh lệch giữa-arm (kiểm định ghép cặp trên trung bình theo câu). Hạn chế: tốn quota (mỗi lượt ~122 request LLM, file 09 §3.5) và với temperature 0 phương sai có thể nhỏ. `[GENERAL]` — repo **không** làm; hạn chế "one run per arm" được ghi là threat. [REPO docs/reports/epics/EPIC-06-experiment.md:120-122]
</details>

## Self-check questions
1. Thí nghiệm này đổi biến nào và giữ hằng những gì? Máy kiểm chuyện đó thế nào?
2. Vì sao hit@5 bằng nhau mà evidence hit@1 và token lại khác?
3. Kết quả duy nhất đáng tin là gì? Vì sao accuracy thì không?
4. Ca 001 cho thấy điều gì về ngưỡng cổng?
5. Cây phân loại lỗi có thứ tự thế nào? Vì sao thứ tự quan trọng?
6. Nêu hai "lỗi phía đo lường" và cách phát hiện chúng.
7. Báo cáo kết luận gì và **không** kết luận gì?

## Interview Q&A
1. **"Kể về một thí nghiệm bạn thiết kế."** — Chỉ đổi chunker, mọi thứ khác giữ hằng và máy kiểm; bộ câu hỏi đóng băng; kiểm định ghép cặp; đọc từng ca ở mức chunk; kết luận đúng mức ([REPO docs/reports/epics/EPIC-06-experiment.md:17-21]).
2. **"Kết quả không có ý nghĩa thống kê thì bạn làm gì?"** — Nói rõ "không đủ bằng chứng", trình bày CI, và đào xuống cơ chế (chunk-level) để rút bài học thay vì bịa kết luận ([REPO docs/reports/epics/EPIC-06-experiment.md:556-571]).
3. **"Làm sao biết lỗi do hệ thống hay do cách đo?"** — Đọc từng ca bất đồng, đọc `reason` của judge, đối chiếu spot-check của người ([REPO docs/reports/epics/EPIC-06-experiment.md:534-554]).
4. **"Vì sao giữ Arm A khi accuracy B nhỉnh hơn?"** — Vì khác biệt accuracy không đáng tin; A rẻ hơn 494 token, giữ code nguyên, citation thẳng hàng section; lựa chọn dựa vào chi phí và cơ chế đo được ([REPO docs/reports/epics/EPIC-06-experiment.md:575-580]).
5. **"Cache ảnh hưởng thí nghiệm ra sao?"** — Tiết kiệm quota nhưng gây confounding độ trễ (`embed_query` B 0.1 ms vs A 352 ms), nên độ trễ không được kiểm định ([REPO docs/reports/epics/EPIC-06-experiment.md:113-118]).
6. **"Bạn đề xuất gì tiếp theo?"** — Ngưỡng theo từng arm, hybrid retrieval + đa dạng hoá biến thể, viết lại truy vấn VI→EN, mỗi cái kèm metric thành công định trước ([REPO docs/reports/epics/EPIC-06-experiment.md:586-603]).

## Further reading
- Kohavi, Tang, Xu, *Trustworthy Online Controlled Experiments* — sách về A/B test nghiêm túc (kiểm soát biến, guardrail metric). `[GENERAL]`
- Es et al., *RAGAS* (arXiv:2309.15217) và các bài đánh giá RAG khác — so sánh với cách đo thủ công ở đây. `[GENERAL]`
- Quay lại: [07](07-chunking-and-retrieval.md) (hai chunker), [10](10-evaluation-design.md), [11](11-llm-as-judge.md), [12](12-statistics-for-experiments.md).
