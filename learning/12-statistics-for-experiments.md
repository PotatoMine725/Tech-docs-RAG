# 12 · Thống kê cho thí nghiệm: kiểm định ghép cặp, bootstrap, phân vị, luật diễn đạt, sức mạnh thống kê
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [10](10-evaluation-design.md), [11](11-llm-as-judge.md) · Study time: ~8–10h · Home file của: thiết kế ghép cặp (paired), McNemar exact, Wilcoxon signed-rank exact, paired bootstrap CI, percentile nearest-rank, p-value/CI, luật diễn đạt (wording rule), power/n nhỏ, so sánh nhiều metric
> Bài tập chạy được: `learning/_tools/exercises/judge_stats_scenarios.py` (mục S2–S5; offline, không mạng, không key). Không cần scipy: repo tự cài đặt bằng Python thuần.

## Vì sao file này quan trọng trong dự án
Thí nghiệm chính của đề bài là so hai cách chunking. Có hai kiểu sai kinh điển: (1) thấy Arm B `0.742` cao hơn Arm A `0.710` rồi tuyên bố "B tốt hơn"; (2) thấy không có khác biệt rồi tuyên bố "hai arm bằng nhau". Thống kê cho bạn ngôn ngữ để nói **chính xác** điều dữ liệu cho phép nói. Module `stats.py` của repo nhỏ (140 dòng), đọc được trong một buổi, và là ví dụ đẹp về việc cài đặt **đúng, xác định, kiểm thử được** những phép thử nền tảng — nên rất đáng học chậm.

---

## Level 1 — Basic

### 1.1 Mô tả (descriptive) vs suy luận (inferential)
- **Ý tưởng:** *mô tả*: "trên 32 câu, Arm A trúng 30". *Suy luận*: "khác biệt giữa hai arm có phải do chunker hay chỉ do may rủi của 32 câu này?". Mọi bảng so sánh trong dự án có cả hai: giá trị mỗi arm (mô tả) và `p`, CI (suy luận). [REPO docs/snapshots/experiments/exp-001.md:19-30]
- **C# analogy:** mô tả giống `Average()`; suy luận giống việc hỏi "nếu chạy lại benchmark, chênh lệch này có còn không?" (BenchmarkDotNet báo cả trung bình lẫn khoảng sai số).
- **Tại sao:** mẫu chỉ 36 câu; một câu đổi kết quả làm tỉ lệ dịch ~3 điểm %. Không có suy luận thì mọi số đều dễ bị hiểu quá.

### 1.2 Thiết kế **ghép cặp** (paired)
- **Ý tưởng:** cùng một câu hỏi chạy trên cả hai arm, nên so **mỗi câu với chính nó**. Độ khó câu hỏi triệt tiêu; chỉ chunker khác. Với hai mảng `a` và `b` cùng độ dài, `a[i]` và `b[i]` thuộc cùng câu `i`. [REPO src/knowledge_assistant/application/evaluation/stats.py:1-8]
- **Trong code:** kiểm tra đầu vào rất nhỏ nhưng quan trọng:
**`src/knowledge_assistant/application/evaluation/stats.py:22-24`**
```python
def _paired(a, b) -> None:
    if len(a) != len(b):
        raise ValueError(f"paired samples need equal lengths, got {len(a)} and {len(b)}")
```
- **Quy ước dấu:** mọi chênh lệch là `B − A` (cột Δ của bảng). Dương = B cao hơn. [REPO src/knowledge_assistant/application/evaluation/stats.py:4]
- **Tại sao ghép cặp:** một phép thử **không ghép** (hai nhóm độc lập) bỏ phí thông tin "cùng câu"; nó cần nhiều dữ liệu hơn để phát hiện cùng chênh lệch.
- **Pitfalls:** báo cáo thí nghiệm ghi rõ: accuracy Arm A là `22/31 = 0.710` (ghép cặp, chỉ những câu có nhãn ở cả hai arm), khác `23/32 = 0.719` (không ghép). Mỗi dòng bảng mang `n` riêng. [REPO docs/reports/epics/EPIC-06-experiment.md:66-81]

### 1.3 p-value và khoảng tin cậy (CI) — nói đúng nghĩa
- **p-value:** xác suất (giả sử **không có khác biệt thật**, tức H0) thấy dữ liệu **cực đoan bằng hoặc hơn** cái đã thấy. p nhỏ = "dữ liệu khó chấp nhận nếu không có khác biệt". **Không** phải xác suất H0 đúng.
- **CI 95% của Δ:** khoảng giá trị Δ "chấp nhận được" theo dữ liệu. Nếu khoảng chứa 0 thì ta không loại được khả năng "không khác biệt". Ví dụ accuracy: `Δ = +0.032`, CI `[−0.097, 0.161]` → chứa 0. [REPO docs/snapshots/experiments/exp-001.md:26]
- **Ngưỡng:** `ALPHA = 0.05`. [REPO src/knowledge_assistant/application/evaluation/experiment.py:39]
- **Tại sao báo cả hai:** p nói "có khác biệt không"; CI nói "khác biệt cỡ nào, không chắc chắn ra sao" — quan trọng hơn khi n nhỏ.
- **Pitfalls `[GENERAL]`:** "không có ý nghĩa thống kê" **không** có nghĩa là "hai bên bằng nhau" (absence of evidence ≠ evidence of absence). Xem luật diễn đạt ở 2.5.

### 1.4 Trung bình, trung vị và **phân vị nearest-rank**
- **Ý tưởng:** với độ trễ (lệch phải, vài lời gọi rất chậm), **trung vị (p50)** và **p95** phản ánh trải nghiệm tốt hơn trung bình. Phương pháp **nearest-rank**: sắp `n` giá trị tăng dần; phân vị thứ p là giá trị ở **hạng** `ceil(p/100 × n)` (đếm từ 1). Không nội suy → mọi phân vị báo cáo là giá trị **thực sự đo được**. [REPO docs/specs/evaluation-spec.md:79]
**`src/knowledge_assistant/application/evaluation/metrics/latency.py:19-27`**
```python
def nearest_rank(values: list[float], p: float) -> float:
    """The p-th percentile by nearest rank; exact rational rank, so float rounding never shifts it."""
    if not values:
        raise ValueError("percentile of no values")
    if not 0 < p <= 100:
        raise ValueError(f"p must be in (0, 100], got {p}")
    ordered = sorted(values)
    rank = math.ceil(Fraction(str(p)) * len(ordered) / 100)
    return ordered[max(rank, 1) - 1]
```
- **Đọc chậm:** `Fraction(str(p)) * len(ordered) / 100` là **số hữu tỉ chính xác** (không phải float) nên `ceil` không bị sai do làm tròn nhị phân (đã chạy thử: với float, `7/100*100` ra `7.000000000000001` nên `math.ceil` cho `8`, còn cách dùng `Fraction` cho đúng hạng `7` trên `[1..100]`, mục S2); `max(rank, 1)` bảo vệ `p` rất nhỏ.
- **Đã chạy thử offline** (mục S2): với `[10,20,...,100]`: p10=`10`, p50=`50`, p51=`60`, p90=`90`, p95=`100`, p100=`100`; `nearest_rank([5], 95)` = `5`; `nearest_rank([3,1,2], 50)` = `2` (tự sắp xếp).
- **Tại sao p95 = giá trị lớn nhất khi n = 10:** `ceil(0.95×10) = 10`. Với mẫu nhỏ, p95 gần như chính là max — con số không có nhiều ý nghĩa.
- **Pitfalls `[GENERAL]`:** thư viện khác (NumPy, Excel) mặc định **nội suy tuyến tính**, cho p50 của `[1,2,3,4]` là `2.5`; nearest-rank cho `2`. Khi so số liệu giữa công cụ, phải cùng phương pháp.

---

## Level 2 — Intermediate

### 2.1 McNemar exact: so hai **tỉ lệ ghép cặp** (nhị phân)
- **Ý tưởng:** với kết quả 0/1 (hit hay không, đúng hay không), chỉ những cặp **bất đồng** (discordant) mới mang thông tin: `b` = cặp A=1,B=0 (chỉ A đúng); `c` = cặp A=0,B=1 (chỉ B đúng). Cặp cùng đúng/cùng sai bị bỏ qua. Nếu **không có khác biệt thật** thì mỗi cặp bất đồng nghiêng về A hay B với xác suất 1/2 → `b` ~ Binomial(`b+c`, 1/2). `p = min(1, 2 × P(X ≤ min(b,c)))`.
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
- **Đọc chậm:** `sum(1 for x, y in zip(a, b) if bool(x) and not bool(y))` đếm b bằng biểu thức generator; `math.comb(n, i)` là tổ hợp; `Fraction(tổng, 2 ** n)` là xác suất **chính xác** (không sai số float); `min(Fraction(1), 2 * tail)` giới hạn p ≤ 1; nhánh `n == 0` (không cặp bất đồng) trả `p = 1.0`.
- **Đã chạy thử offline** (mục S3) — tái tạo đúng các dòng bảng của báo cáo:
  | Trường hợp | b | c | p (chạy thử) | Bảng thật |
  |---|---|---|---|---|
  | accuracy | 2 | 3 | `1.0` | `1.000` |
  | evidence hit@1 | 11 | 5 | `0.2101` | `0.210` |
  | section hit@5 | 1 | 1 | `1.0` | `1.000` |
  | 5–0 | 5 | 0 | `0.0625` | (ví dụ trong báo cáo) |
  Tính tay `b=11, c=5`: `n = 16`; `Σ_{i≤5} C(16,i) = 1+16+120+560+1820+4368 = 6885`; `6885/65536 = 0.10506`; nhân 2 = `0.2101`.
- **C# analogy:** không có trong BCL; ML.NET/Accord.NET có; ý tưởng giống một **sign test** trên các cặp bất đồng.
- **Tại sao "exact" thay vì xấp xỉ chi-bình phương:** với n nhỏ (b+c = 5, 16) xấp xỉ chuẩn không tin cậy; tính trực tiếp từ nhị thức là **chính xác** và rẻ.
- **Pitfalls `[GENERAL]`:** McNemar chỉ áp cho **dữ liệu ghép cặp nhị phân**; dùng cho hai nhóm độc lập là sai. Và nó **không nhìn** các cặp đồng ý, nên hai arm cùng đạt 30/32 vẫn có thể bất đồng ở 2 câu khác nhau — repo liệt kê từng câu bất đồng (`a_only`, `b_only`) để người đọc thấy. [REPO src/knowledge_assistant/application/evaluation/experiment.py:161-184]

### 2.2 Vì sao "5–0" cũng chưa đủ (sức mạnh thống kê, power)
- **Sự thật rút từ công thức:** với `b+c = n` cặp bất đồng, giá trị p **nhỏ nhất** có thể đạt là `2/2ⁿ` (khi toàn bộ nghiêng một phía). `n=5` → `2/32 = 0.0625 > 0.05`. Cần `n ≥ 6` bất đồng (`2/64 = 0.031`) mới có thể đạt `p < 0.05`. Báo cáo dùng đúng ví dụ này. [REPO docs/reports/epics/EPIC-06-experiment.md:107-111]
- **Áp vào dữ liệu thật:** accuracy có **5** cặp bất đồng (`020`, `027` A-only; `001`, `012`, `022` B-only). Dù tất cả nghiêng một phía cũng chỉ `p = 0.0625`. Vậy "không khác biệt đáng tin" ở đây nghĩa là **"quá ít bất đồng để kết luận"**, không phải "hai arm bằng nhau".
- **Ý nghĩa thực hành:** với `n = 36` chỉ **hiệu ứng lớn** mới đạt ý nghĩa; để phát hiện chênh lệch nhỏ cần nhiều câu hơn (hoặc chạy lặp). Tính power đầy đủ `[GENERAL]` cần giả định về kích thước hiệu ứng; repo không tính (xem 3.3).
- **Tại sao quan trọng:** phần "n = 36 nhỏ" trong threats to validity (file 10 §3.2) dựa trên chính công thức này.

### 2.3 Wilcoxon signed-rank exact: so hai đại lượng **liên tục** ghép cặp
- **Ý tưởng:** với độ trễ, token, MRR (không phải 0/1) dùng `d = b − a`: bỏ `d = 0`; xếp hạng `|d|` (hòa → hạng trung bình); cộng hạng của `d > 0` thành `W+` (và `d < 0` thành `W−`). Nếu không có khác biệt thật, dấu của mỗi hạng là ± ngẫu nhiên xác suất 1/2 → có thể **liệt kê phân phối chính xác** của `W+`. Hai đuôi: `p = min(1, 2 × min(P(W+ ≤ w), P(W+ ≥ w)))`.
**`src/knowledge_assistant/application/evaluation/stats.py:114-127`**
```python
def wilcoxon_signed_rank(a: list[float], b: list[float]) -> WilcoxonResult:
    """Exact Wilcoxon signed-rank test on d = b - a.

    Zero differences are dropped (Wilcoxon's method); ties get average ranks. The p-value comes from the exact
    permutation distribution of W+ given these ranks (each sign +/- with probability 1/2), counted with a subset-sum
    table over doubled ranks (average ranks are multiples of 0.5). It is exact with ties too, where scipy would switch
    to a normal approximation, so tied cases can differ slightly from scipy. p = min(1, 2 * min(P(W+ <= w), P(W+ >= w))).
    """
    _paired(a, b)
    differences = [round(y - x, TIE_DECIMALS) for x, y in zip(a, b)]
    nonzero = [d for d in differences if d != 0]
    zeros = len(differences) - len(nonzero)
    if not nonzero:
        return WilcoxonResult(0, zeros, 0.0, 0.0, 1.0)
```
**`src/knowledge_assistant/application/evaluation/stats.py:128-140`**
```python
    ranks = _average_ranks([abs(d) for d in nonzero])
    w_plus = sum(r for r, d in zip(ranks, nonzero) if d > 0)
    w_minus = sum(r for r, d in zip(ranks, nonzero) if d < 0)
    doubled = [round(2 * r) for r in ranks]
    counts = [1] + [0] * sum(doubled)  # counts[s] = number of sign patterns with doubled W+ = s
    for rank in doubled:
        for total in range(len(counts) - 1, rank - 1, -1):
            counts[total] += counts[total - rank]
    observed = round(2 * w_plus)
    patterns = 2 ** len(nonzero)
    lower = Fraction(sum(counts[: observed + 1]), patterns)
    upper = Fraction(sum(counts[observed:]), patterns)
    return WilcoxonResult(len(nonzero), zeros, w_plus, w_minus, float(min(Fraction(1), 2 * min(lower, upper))))
```
- **Đọc chậm (phần khó nhất của file):**
  - `differences = [round(y - x, TIE_DECIMALS) ...]`: **làm tròn 12 chữ số** để `0.1 + 0.2` và `0.3` được coi bằng nhau (nhiễu float không tạo ra chênh lệch giả). Đã chạy thử: `wilcoxon_signed_rank([0.1+0.2],[0.3])` → `n=0, zeros_dropped=1` (mục S4).
  - `_average_ranks`: xếp hạng có hòa — hai giá trị bằng nhau nhận hạng trung bình (ví dụ hạng 2 và 3 → cả hai `2.5`). [REPO src/knowledge_assistant/application/evaluation/stats.py:99-111]
  - `doubled = [round(2 * r) ...]`: vì hạng trung bình là bội của `0.5`, nhân đôi để thành **số nguyên** dùng làm chỉ số bảng.
  - `counts = [1] + [0] * sum(doubled)` rồi hai vòng `for` là **quy hoạch động kiểu "subset-sum"**: `counts[s]` = số cách chọn dấu sao cho tổng hạng (đã nhân đôi) bằng `s`. Vòng `for total in range(len(counts) - 1, rank - 1, -1)` **chạy ngược** để mỗi hạng chỉ được dùng một lần (mẫu knapsack 0/1).
  - `patterns = 2 ** len(nonzero)` là tổng số tổ hợp dấu; `lower`/`upper` là xác suất chính xác hai đuôi.
- **Đã chạy thử offline** (mục S4): cả 5 cặp `b − a = +1` → `n=5, w_plus=15.0, w_minus=0, p=0.0625` (khớp với suy luận `2/32` ở 2.2); toàn cặp bằng nhau → `n=0, zeros_dropped=3, p=1.0`.
- **Tại sao tự cài thay vì scipy:** docstring ghi "scipy is not installed"; bản tự cài **chính xác cả khi có hòa** (scipy sẽ chuyển sang xấp xỉ chuẩn), nên có thể lệch nhẹ scipy ở ca hòa. Đó là lựa chọn có ý thức và được ghi. [REPO src/knowledge_assistant/application/evaluation/stats.py:117-120]
- **C# analogy:** không có sẵn trong BCL; nếu dùng .NET bạn sẽ thêm MathNet hoặc tự cài như ở đây.
- **Pitfalls `[GENERAL]`:** Wilcoxon giả định phân phối của `d` **đối xứng** quanh trung vị; với dữ liệu lệch nặng kết luận cần thận trọng. Ví dụ dữ liệu lệch trong repo: độ trễ `generate` có p50 ≈ 1.5 s nhưng p95 ≈ 37–39 s vì vài lời gọi rất chậm ([REPO docs/reports/epics/EPIC-06-experiment.md:117-118]). **Đây không phải lý do** báo cáo không kiểm định `embed_query` và `total`: lý do của báo cáo là **confounding** do thứ tự chạy và cache (Arm B toàn cache hit), xem §3.3 ([REPO docs/reports/epics/EPIC-06-experiment.md:113-116]).

### 2.4 Paired bootstrap: khoảng tin cậy không cần công thức
- **Ý tưởng:** không biết phân phối của Δ thì **giả lập** nó: từ `n` cặp, lấy mẫu **có hoàn lại** `n` **chỉ số** (cả hai arm cùng chỉ số → cặp giữ nguyên), tính `mean(B) − mean(A)`; lặp 10 000 lần; CI 95% = phân vị 2.5 và 97.5 của các Δ giả lập. Hạt giống cố định (`seed 42`) để **tái lập**.
**`src/knowledge_assistant/application/evaluation/stats.py:63-81`**
```python
def paired_bootstrap_ci(a: list[float], b: list[float], resamples: int = BOOTSTRAP_RESAMPLES,
                        seed: int = BOOTSTRAP_SEED, confidence: float = 0.95, statistic=_mean) -> BootstrapResult:
    """Percentile CI of statistic(B) - statistic(A), resampling case indices (pairs stay together).

    `random.Random(seed)` draws n indices with replacement per resample; the bounds are the nearest-rank
    (1 - confidence) / 2 and (1 + confidence) / 2 percentiles of the resampled differences.
    """
    _paired(a, b)
    if not a:
        raise ValueError("bootstrap of no pairs")
    rng = random.Random(seed)
    n = len(a)
    deltas = []
    for _ in range(resamples):
        indices = [rng.randrange(n) for _ in range(n)]
        deltas.append(statistic([b[i] for i in indices]) - statistic([a[i] for i in indices]))
    low, high = percentile_interval(deltas, confidence)
    return BootstrapResult(delta=statistic(b) - statistic(a), low=low, high=high, confidence=confidence,
                           resamples=resamples, seed=seed)
```
**`src/knowledge_assistant/application/evaluation/stats.py:84-87`**
```python
def percentile_interval(values: list[float], confidence: float = 0.95) -> tuple[float, float]:
    """Nearest-rank (1 - confidence) / 2 and (1 + confidence) / 2 percentiles of `values`."""
    tail = (1 - Fraction(str(confidence))) / 2 * 100  # exact: 0.95 -> 5/2, not 2.500000000000002
    return nearest_rank(values, tail), nearest_rank(values, 100 - tail)
```
- **Đọc chậm:** `random.Random(seed)` là **bộ sinh ngẫu nhiên cục bộ** (không đụng trạng thái toàn cục); `[rng.randrange(n) for _ in range(n)]` là chỉ số có hoàn lại; `statistic=_mean` là **hàm làm tham số** (first-class function) nên có thể bootstrap thống kê khác. `Fraction(str(confidence))`: `0.95 → 19/20`, do đó `tail = 5/2` chính xác — không phải `2.500000000000002`.
- **Đã chạy thử offline** (mục S5): 8 cặp nhị phân, 2000 lần → `delta = 0.25`, CI `[-0.25, 0.625]`; chạy hai lần → **kết quả giống hệt** (`True`); `percentile_interval(1..100)` → `(3, 98)` (nearest-rank: `ceil(2.5) = 3`, `ceil(97.5) = 98`).
- **Tại sao ghép chỉ số thay vì ghép giá trị:** giữ nguyên tương quan giữa A và B trên cùng câu; lấy mẫu riêng từng arm sẽ phá thiết kế ghép cặp.
- **Pitfalls `[GENERAL]`:** bootstrap không "tạo dữ liệu mới" — với n rất nhỏ khoảng tin cậy vẫn thiếu tin cậy (ở ví dụ trên `[-0.25, 0.625]` rất rộng). Và seed cố định giúp tái lập nhưng **không** làm CI chính xác hơn.

### 2.5 Luật diễn đạt (wording rule) và bảng kết quả
- **Luật:** `p ≥ 0.05` ⇒ viết **"no statistically reliable difference at n = X"**, **không bao giờ** "A tốt hơn". Chỉ khi `p < 0.05` mới được nói "B higher/lower than A" kèm `p` và `n`. [REPO src/knowledge_assistant/application/evaluation/stats.py:8]
**`src/knowledge_assistant/application/evaluation/experiment.py:152-158`**
```python
def wording(p_value: float | None, n: int, delta: float) -> str:
    """EXP-001 wording rule: p >= 0.05 never names a winner."""
    if p_value is None:
        return "not tested"
    if p_value >= ALPHA:
        return f"no statistically reliable difference at n = {n}"
    return f"B {'higher' if delta > 0 else 'lower'} than A (p = {p_value:.3g}, n = {n})"
```
- **Bảng một dòng** do `compare` tạo: loại metric quyết định phép thử — nhị phân → McNemar; liên tục → Wilcoxon; mô tả → chỉ trung vị hai arm; **mọi** loại có bootstrap CI (trừ mô tả). Kết quả kèm `n`, danh sách câu (`cases`), `a_only`/`b_only`. [REPO src/knowledge_assistant/application/evaluation/experiment.py:161-183]
- **Tại sao quy tắc này nằm trong code chứ không chỉ trong tài liệu:** để **không ai** viết tay câu kết luận vượt dữ liệu; câu chữ được sinh cùng số.
- **Ví dụ kết luận đúng với dữ liệu thật:** "chênh lệch prompt token/answer `+494.0` (CI `[418.8, 567.2]`, Wilcoxon p < 0.001, n = 30) là đáng tin; accuracy `+0.032` (McNemar p = 1.0, n = 31) thì không". [REPO docs/snapshots/experiments/exp-001.md:26-29]
- **Pitfalls `[GENERAL]`:** trước khi kiểm định, luôn quyết định **trước** metric chính (primary) — repo đã đặt bảng và luật trước khi xem kết quả (`EXP-001` §1).

---

## Level 3 — Advanced

### 3.1 So sánh **nhiều metric**: cạm bẫy tỉ lệ dương tính giả
- **Vấn đề `[GENERAL]`:** báo cáo so sánh hàng chục metric (source/section × @1/@3/@5 × lenient/strict, evidence hit, accuracy, citation…). Mỗi phép thử ở `α = 0.05` có 5% cơ hội "có ý nghĩa" chỉ vì may; chạy ~30 phép thử thì **kỳ vọng vài cái** qua ngưỡng dù không có khác biệt thật. Cách xử lý chuẩn: hiệu chỉnh (Bonferroni, Holm) hoặc chọn **metric chính** trước.
- **Trong repo (sự thật kiểm được):** danh sách metric được xây trong `experiment.py` (vòng `for level` × `for k`) và mỗi cái được kiểm riêng. Tôi chạy `git grep` (không phân biệt hoa thường) trên `docs/`, `src/`, `scripts/`, `README.md`, `AI_WORKLOG.md` ở commit đã ghim với các từ *multiple comparison/testing*, *Bonferroni*, *Holm*, *family-wise*, *false discovery*, *multiplicity*: **không có kết quả liên quan** (các hit còn lại là từ "correct" thông thường). Kết luận đúng mức: *no correction found (grep của các thư mục trên)* — `[UNVERIFIED]` vì tôi không đọc từng dòng của toàn bộ các báo cáo. [REPO src/knowledge_assistant/application/evaluation/experiment.py:94-103]
- **Vì sao ở đây ít rủi ro thực tế:** trong bảng headline của snapshot mọi p ≥ 0.2 trừ chênh lệch prompt token (một phép đo gần như xác định), nên không có "phát hiện" nào bị thổi phồng ở đó (tôi không đọc từng dòng của toàn bộ bảng đầy đủ nên không khẳng định gì về chúng), nên không có "phát hiện" nào bị thổi phồng. Nhưng nếu một metric đạt `p = 0.04` trong ~30 cái, bạn **không** nên coi đó là bằng chứng mạnh. `[GENERAL]`
- **Tại sao học điều này:** khi bạn thấy "một trong 30 metric có ý nghĩa" trong bài báo/báo cáo khác, câu hỏi phản biện đầu tiên là về hiệu chỉnh nhiều phép thử.

### 3.2 Ý nghĩa thống kê ≠ ý nghĩa thực tiễn; không khác biệt ≠ tương đương
- **Kích thước hiệu ứng:** chênh lệch `+494` prompt token/answer là **rất đáng tin** (p < 0.001) và cũng **có ý nghĩa thực tế** (Arm B tốn ~30% token hơn: `2122.6/1628.6 ≈ 1.30`). Chênh lệch accuracy `+0.032` **không** đáng tin và cũng nhỏ. Hai trục khác nhau: *độ chắc chắn* (p, CI) vs *độ lớn* (Δ).
- **Không khác biệt ≠ tương đương:** để chứng minh hai arm **tương đương** cần kiểm định tương đương (TOST) với biên chấp nhận được `[GENERAL]`; repo **không** tuyên bố tương đương, chỉ tuyên bố "chưa đủ bằng chứng để nói khác". Đúng mức. [REPO docs/reports/epics/EPIC-06-experiment.md:17-21]
- **Pitfalls:** báo cáo "hai arm bằng nhau" từ p = 1.0 là sai lầm phổ biến nhất khi đọc kết quả A/B.

### 3.3 Nhiễu cấu trúc: cái thống kê không cứu được
Báo cáo tự liệt kê những thứ **kiểm định không sửa được**: [REPO docs/reports/epics/EPIC-06-experiment.md:85-122]
- **Độ trễ bị nhiễu bởi thứ tự chạy và cache:** Arm A chạy trước và tính embedding live; Arm B toàn cache hit (`embed_query` p50 0.1 ms vs 352 ms). Đây là **confounder** — không có phép thử nào biến số đó thành so sánh công bằng. Vì vậy `embed_query` và `total` được **trình bày mà không kiểm định**.
- **Một lần chạy mỗi arm:** thay đổi nhãn của một câu có thể là **phương sai sinh câu trả lời** (LLM) chứ không phải chunker; thiết kế này không tách được hai thứ.
- **Ngưỡng cổng chỉnh trên Arm A:** thiên lệch cấu trúc, không phải lỗi thống kê (file 10 §3.2).
- **Bài học:** thống kê chỉ đo **nhiễu ngẫu nhiên**. Sai lệch hệ thống (bias, confounding) phải bị loại bằng **thiết kế** (kiểm soát biến, chạy lặp, đối chứng).

### 3.4 Tính tái lập: seed, `Fraction`, và dữ liệu đã hash
- **Seed cố định** (`42`), `random.Random(seed)` cục bộ → cùng đầu vào cho **cùng** CI. `Fraction` thay float ở các chỗ cần chính xác (McNemar, phân vị, ngưỡng CI). `TIE_DECIMALS` xử lý nhiễu float. [REPO src/knowledge_assistant/application/evaluation/stats.py:17-19]
- **Script so sánh từ chối chạy** nếu các thiết lập "giữ hằng" giữa hai run khác nhau, và snapshot ghi SHA-256 của mọi file đầu vào. [REPO docs/reports/epics/EPIC-06-experiment.md:33-34], [REPO docs/snapshots/experiments/exp-001.md:6-17]
- **Tại sao:** kết quả thí nghiệm chỉ là **bằng chứng** khi người khác chạy lại được đúng số đó.
- **Pitfalls `[GENERAL]`:** bootstrap không seed cho CI khác nhau mỗi lần chạy — người đọc báo cáo không thể tái tạo được bảng.

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Tính p-value McNemar cho `b = 4, c = 0`. Có "có ý nghĩa" ở 0.05 không?
<details><summary>Đáp án</summary>
`n = 4`, `min(b,c) = 0`, `Σ C(4,0) = 1`, `tail = 1/16`, `p = 2/16 = 0.125 ≥ 0.05` → **không**. Ngay cả 4–0 cũng chưa đủ; như đã nói cần `n ≥ 6` bất đồng một phía. (Công thức đã được kiểm với các dòng `5–0 → 0.0625`, `2–3 → 1.0`, `11–5 → 0.2101` ở mục S3.) [REPO src/knowledge_assistant/application/evaluation/stats.py:34-46]
</details>

**B2 (Basic).** Nearest-rank p50 và p95 của `[8, 3, 5, 1, 9, 7, 2, 6, 4, 10]`?
<details><summary>Đáp án</summary>
Sắp xếp `1..10`; `n = 10`. p50: rank `ceil(5.0) = 5` → **5**. p95: rank `ceil(9.5) = 10` → **10**. (Mục S2 kiểm cùng cách trên `[10,20,…,100]` → 50 và 100.) [REPO src/knowledge_assistant/application/evaluation/metrics/latency.py:19-27]
</details>

**B3 (Basic).** Vì sao dùng thiết kế ghép cặp thay vì so trung bình hai nhóm độc lập?
<details><summary>Đáp án</summary>
Cùng câu hỏi trên cả hai arm nên độ khó **triệt tiêu**; phép thử ghép cặp chỉ dựa trên chênh lệch theo từng câu, nhạy hơn với cùng n. [REPO docs/reports/epics/EPIC-06-experiment.md:58-60]
</details>

**I1 (Intermediate).** Tính tay p McNemar cho `b = 3, c = 8` (n = 11) rồi kiểm bằng code.
<details><summary>Đáp án</summary>
`min = 3`; `Σ_{i≤3} C(11,i) = 1 + 11 + 55 + 165 = 232`; `232/2048 = 0.11328`; `p = 0.2266`. Chạy `mcnemar_exact([1]*3+[0]*8, [0]*3+[1]*8)` để đối chiếu (cùng hàm đã cho các số ở S3).
</details>

**I2 (Intermediate).** `wilcoxon_signed_rank([1,2,3,4,5],[2,3,4,5,6])` cho `p` bao nhiêu? Giải thích bằng công thức `2/2ⁿ`.
<details><summary>Đáp án</summary>
Cả năm `d = +1` → hạng bằng nhau (hòa, hạng trung bình `3`), `W+ = 15`, chỉ **một** trong `2⁵ = 32` tổ hợp dấu cho `W+` lớn như vậy → `p = 2 × 1/32 = 0.0625` (đã chạy: `n=5, w_plus=15.0, w_minus=0, p_value=0.0625`, mục S4). [REPO src/knowledge_assistant/application/evaluation/stats.py:114-140]
</details>

**I3 (Intermediate).** Chạy bootstrap hai lần với cùng dữ liệu nhưng **không** đặt seed cố định (ví dụ `random.Random()` không tham số). Kết quả thế nào và vì sao repo cố định seed?
<details><summary>Đáp án</summary>
Hai lần cho hai CI hơi khác nhau (nhiễu Monte-Carlo); với seed cố định thì **giống hệt** (đã chạy: `c1 == c2` là `True`, mục S5). Cố định seed để bảng kết quả **tái lập** và kiểm được bởi người khác. [REPO src/knowledge_assistant/application/evaluation/stats.py:17-18, 63-81]
</details>

**A1 (Advanced).** Vì sao vòng `for total in range(len(counts) - 1, rank - 1, -1)` phải chạy **ngược**? Điều gì sai nếu chạy xuôi?
<details><summary>Đáp án</summary>
Đây là knapsack **0/1**: mỗi hạng chỉ được chọn tối đa một lần cho mỗi tổ hợp dấu. Chạy ngược đảm bảo `counts[total - rank]` chưa bị cập nhật bởi **chính hạng đó** trong lượt này. Chạy xuôi sẽ cho phép dùng cùng một hạng nhiều lần (knapsack không giới hạn), đếm quá số tổ hợp và cho p-value sai. [REPO src/knowledge_assistant/application/evaluation/stats.py:132-135]
</details>

**A2 (Advanced).** Bạn chạy 30 phép thử ở `α = 0.05`; kỳ vọng bao nhiêu phép thử "có ý nghĩa" nếu **không có** khác biệt thật? Nêu hai cách xử lý.
<details><summary>Đáp án</summary>
Xấp xỉ `30 × 0.05 = 1.5` phép thử. Cách xử lý: hiệu chỉnh nhiều phép thử (Bonferroni: `α/30 ≈ 0.0017`; Holm) hoặc **chọn trước một metric chính** và coi phần còn lại là thăm dò. Repo báo cáo tất cả kèm `n`, `p`, CI, không hiệu chỉnh (`grep` không thấy) — điều này được ghi ở 3.1. `[GENERAL]` cho biện pháp; phần "repo không hiệu chỉnh" là sự kiện kiểm được.
</details>

**A3 (Advanced).** Đọc dòng "prompt tokens / answer: A 1,628.6, B 2,122.6, Δ +494.0, CI [418.8, 567.2], Wilcoxon p < 0.001, n = 30". Viết **một câu** kết luận đúng luật diễn đạt, và một câu bạn **không** được viết.
<details><summary>Đáp án</summary>
Được viết: "Arm B gửi nhiều hơn khoảng 494 prompt token mỗi câu trả lời (CI 95% [419, 567], Wilcoxon p < 0.001, n = 30)." Không được viết: "Arm B tốt hơn/tệ hơn" hay "hai arm không khác nhau về chi phí" — thứ nhất vì chi phí token là một trục, không phải chất lượng; thứ hai vì kết quả ở đây **có** khác biệt đáng tin. [REPO docs/snapshots/experiments/exp-001.md:29]
</details>

## Self-check questions
1. Vì sao thiết kế ghép cặp? `a[i]` và `b[i]` là gì?
2. `b` và `c` trong McNemar nghĩa là gì; những cặp nào bị bỏ qua?
3. Vì sao 5–0 vẫn cho `p = 0.0625`? Cần tối thiểu bao nhiêu cặp bất đồng để `p < 0.05`?
4. Nearest-rank khác nội suy tuyến tính thế nào? Khi nào p95 = max?
5. Bootstrap ghép cặp lấy mẫu **cái gì**? Vì sao?
6. "Không có khác biệt đáng tin" khác "hai arm bằng nhau" ở đâu?
7. Vì sao độ trễ `embed_query` không được kiểm định?

## Interview Q&A
1. **"McNemar test dùng khi nào?"** — So hai tỉ lệ nhị phân trên cùng một tập mẫu (ghép cặp); chỉ dùng các cặp bất đồng; bản exact dùng nhị thức, tốt cho n nhỏ ([REPO src/knowledge_assistant/application/evaluation/stats.py:34-46]).
2. **"Bootstrap là gì, khác t-test thế nào?"** — Giả lập phân phối của thống kê bằng lấy mẫu có hoàn lại, không cần giả định phân phối; ở đây lấy mẫu **chỉ số cặp**, 10 000 lần, seed 42 ([REPO src/knowledge_assistant/application/evaluation/stats.py:63-81]).
3. **"Bạn báo cáo kết quả không có ý nghĩa thế nào?"** — "No statistically reliable difference at n = X" kèm CI; không tuyên bố arm thắng ([REPO src/knowledge_assistant/application/evaluation/experiment.py:152-158]).
4. **"Vì sao tự cài Wilcoxon?"** — scipy không có trong môi trường; bản tự cài chính xác cả khi có hòa; bù lại có thể lệch nhẹ scipy ở ca hòa và điều đó được ghi ([REPO src/knowledge_assistant/application/evaluation/stats.py:117-120]).
5. **"Percentile p95 tính thế nào?"** — Nearest-rank `ceil(p/100 × n)` với số hữu tỉ chính xác, không nội suy ([REPO src/knowledge_assistant/application/evaluation/metrics/latency.py:19-27]).
6. **"Điều gì thống kê không cứu được trong thí nghiệm này?"** — Confounding do thứ tự chạy/cache, một lần chạy mỗi arm, ngưỡng chỉnh trên Arm A ([REPO docs/reports/epics/EPIC-06-experiment.md:85-122]).

## Further reading
- McNemar, Q. (1947) — bài gốc của phép thử. `[GENERAL]`
- Wilcoxon, F. (1945), *Individual comparisons by ranking methods*. `[GENERAL]`
- Efron & Tibshirani, *An Introduction to the Bootstrap* — sách giáo khoa bootstrap. `[GENERAL]`
- Wasserstein & Lazar (2016), *The ASA Statement on p-Values* — cách diễn giải p đúng. `[GENERAL]`
- Python docs: module `fractions`, `math.comb`, `random.Random`. `[GENERAL]` (`https://docs.python.org/3/library/fractions.html`)
- Tiếp theo: [13](13-case-study-exp-001.md) (ca nghiên cứu).
