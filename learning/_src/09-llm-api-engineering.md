# 09 · Kỹ thuật gọi LLM API: rate limit, throttle, retry/backoff, fallback, phân loại lỗi, token, chi phí
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [01](01-python-for-csharp-devs.md), [03](03-architecture-and-gui.md), [06](06-embeddings-and-vector-search.md) · Study time: ~9–11h · Home file của: RPM/TPM/RPD, throttle cửa sổ trượt, retry + backoff + jitter + retry-after, fallback model, phân loại lỗi, quota theo ngày & múi giờ, token/thinking token, ước tính chi phí, che API key
> Bài tập chạy được: `learning/_tools/exercises/llm_retry_scenarios.py` (offline, không mạng, không key).

## Vì sao file này quan trọng trong dự án
Gemini free tier rất hạn chế (15 request/phút và 500/ngày cho model chính; 5 và 20 cho model dự phòng). Một lần đánh giá đầy đủ cần ~120 câu trả lời + ~120 lần chấm. Nếu code gọi API ngây thơ, nó sẽ bị 429, mất kết quả, hoặc lặng lẽ trộn kết quả từ hai model khác nhau. Toàn bộ `gemini_llm.py` + `gemini_retry.py` là một bài học về **độ bền (resilience)** khi làm việc với API bên ngoài.

---

## Level 1 — Basic

### 1.1 Giới hạn tốc độ (rate limit): RPM, TPM, RPD
- **Ý tưởng:** nhà cung cấp giới hạn theo **RPM** (request/phút), **TPM** (token/phút), **RPD** (request/ngày), tính **theo project và theo model**. Vượt → HTTP **429**.
- **Số của dự án** (free tier, chủ dự án đọc từ AI Studio):
  | Model | RPM | TPM | RPD |
  |---|---|---|---|
  | `gemini-3.5-flash-lite` (answer + judge) | 15 | 250K | 500 |
  | `gemini-3.5-flash` (fallback) | 5 | 250K | 20 |
  | `gemini-embedding-001` | 100 | 30K | 1K |
  [REPO docs/architecture/decisions/0004-gemini-model-selection.md:27-33]
- **Trong code:** giới hạn được mô hình hoá thành dataclass, kèm một **throttle** phía client thấp hơn RPM:
@@SNIP src/knowledge_assistant/config.py 71-83@@
  Đọc: `throttle_rpm` phải nằm trong `[1, rpm]` (kiểm ở [REPO src/knowledge_assistant/config.py:129-132]); giá trị mặc định: model chính **13** (giới hạn 15), fallback **4** (giới hạn 5) ([REPO src/knowledge_assistant/config.py:152-153]). TPM và RPD **không** được adapter ép; chúng dùng để **lập kế hoạch** một lần chạy.
- **C# analogy:** `System.Threading.RateLimiting` (`SlidingWindowRateLimiter`) hoặc Polly `RateLimit` policy.
- **Tại sao throttle thấp hơn giới hạn:** "so a run never trips the provider limit" (docstring `ModelLimits`).
- **Pitfalls:** `[GENERAL]` giới hạn free tier thay đổi; các số trên là quan sát ngày 26/09/2026 trong repo, hãy đọc lại trang giới hạn của nhà cung cấp trước khi dùng lại.

### 1.2 Chọn model và "ghim" tên model trong cấu hình
- **Quyết định (ADR-0004):** embedding `gemini-embedding-001`; **trả lời và chấm điểm** `gemini-3.5-flash-lite`; **dự phòng** `gemini-3.5-flash`. Tên model chỉ nằm trong cấu hình, **không hard-code** và **không dùng alias `-latest`** (alias có thể đổi âm thầm, phá tính tái lập). [REPO docs/architecture/decisions/0004-gemini-model-selection.md:43-47]
- **Trong code:**
@@SNIP src/knowledge_assistant/config.py 143-155@@
- **Tại sao model chính là flash-lite:** 500 RPD/15 RPM đủ chạy toàn bộ đánh giá trong một ngày; nhanh nhất khi kiểm thử; app và evaluation dùng **cùng** model nên số liệu báo cáo mô tả đúng hệ thống thật (D11).
- **Pitfalls `[REAL]`:** ADR gốc chọn `gemini-3.5-flash` (20 RPD), nhưng 120+ lần gọi/lượt đánh giá cần ~6 ngày; ADR được **amend** sang flash-lite để đánh giá chạy được trong một ngày. [REPO docs/architecture/decisions/0004-gemini-model-selection.md:62-71]

### 1.3 Token: prompt, output, và "thinking"
- **Ý tưởng:** chi phí và giới hạn tính theo **token** (~4 ký tự tiếng Anh/token). Có **prompt tokens** (đầu vào), **output tokens** (đầu ra), và với một số model có **thinking tokens** (token "suy nghĩ nội bộ"; tính như output khi tính tiền).
- **Trong repo này:** `LLMResponse` mang đủ số liệu; `None` nghĩa là "provider không báo", **không** phải 0:
@@SNIP src/knowledge_assistant/core/interfaces/llm.py 13-33@@
  `latency_ms` = thời gian model của lần gọi tạo ra câu trả lời; **thời gian chờ được tách riêng**: `retry_wait_ms` (backoff giữa các lần thử) và `throttle_wait_ms` (throttle phía client) — để báo cáo độ trễ phân biệt "model chậm" với "mình tự chờ".
- **Tại sao:** ở 13 RPM, một lần chạy đầy đủ bị throttle; nếu không tách, `generate` sẽ bị thổi phồng (ADR-0004 amendment). [REPO docs/architecture/decisions/0004-gemini-model-selection.md:111]
- **Pitfalls `[UNVERIFIED]`:** không biết thinking token có tính vào `max_output_tokens` hay không (SDK không nói, chưa có lần gọi live nào quyết định); repo chỉ ghi lại như hạn chế. [REPO docs/specs/generation-spec.md:55]

### 1.4 Lỗi API thành ba loại: `quota`, `unavailable`, `other`
- **Ý tưởng:** không xử lý theo từng mã HTTP rải rác; phân loại thành ba **kind** để mọi tầng (retry, log, GUI) dùng chung.
  | Kind | Ví dụ | Retry? | Lỗi core |
  |---|---|---|---|
  | `quota` | HTTP 429 (theo phút hoặc theo ngày) | theo phút: có; theo ngày: không | `LLMQuotaError(daily=…)` |
  | `unavailable` | 5xx, timeout, lỗi kết nối | có | `LLMUnavailableError` |
  | `other` | 400/401/403/404, JSON hỏng | **không** | `LLMRequestError` |
  [REPO docs/architecture/decisions/0004-gemini-model-selection.md:92-100]
- **Trong code:**
@@SNIP src/knowledge_assistant/core/exceptions/__init__.py 68-87@@
- **Tại sao:** GUI chỉ cần `kind` để chọn thông báo; `LLMError.kind` ánh xạ 1:1 sang GUI ([REPO src/knowledge_assistant/presentation/desktop/viewmodels/core_ask_question.py:43-51]).
- **Pitfalls:** `[GENERAL]` **400/401/403/404 không retry**: gửi lại cùng một request sai sẽ sai mãi và đốt quota.

---

## Level 2 — Intermediate

### 2.1 Throttle cửa sổ trượt (sliding window) phía client
- **Ý tưởng:** giữ lịch sử `(thời điểm, số request, số token)` trong 60 giây gần nhất; trước mỗi lời gọi kiểm tra "còn chỗ không"; nếu không, **ngủ** đến khi lời gọi cũ nhất rời cửa sổ. Code đầy đủ ở [REPO src/knowledge_assistant/infrastructure/embeddings/throttle.py:17-60] (đã đọc ở file 01b §T20).
- **Dùng cho LLM:** mỗi model có throttle riêng; mọi lần thử (kể cả retry và fallback) đều đi qua:
@@SNIP src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py 63-80@@
  `acquire(0)` ở [REPO src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py:185] truyền `tokens=0` vì **chỉ đếm request** (TPM không ép: 13 request/phút × prompt ~3K token ≪ 250K TPM).
- **Đã chạy thử offline** (file 01 §2.3): throttle `(3, 1000, 60s)` + đồng hồ giả → bốn lần `acquire(10)` chờ `[0,0,0,60]`.
- **Pitfalls `[REAL]`:** bộ đếm throttle sống **trong một tiến trình**: khởi động lại script là đặt lại; và hai instance `GeminiLLM` của cùng model có hai cửa sổ riêng trừ khi chia sẻ `throttles` rõ ràng. [REPO docs/architecture/decisions/0004-gemini-model-selection.md:90]

### 2.2 Retry với backoff luỹ thừa + jitter + `Retry-After`
- **Ý tưởng:** khi lỗi tạm thời, thử lại **sau khi chờ lâu dần** (1s, 2s, 4s…) để không dồn thêm áp lực. **Jitter** (thêm ngẫu nhiên 0–1s) tránh nhiều client cùng retry đúng một lúc. Nếu server nói "hãy chờ N giây" (`Retry-After`), tôn trọng nếu lớn hơn. Trần **120s** để chạy không bao giờ treo im lặng.
- **Trong code:**
@@SNIP src/knowledge_assistant/infrastructure/gemini_retry.py 16-21@@
@@SNIP src/knowledge_assistant/infrastructure/gemini_retry.py 104-108@@
  Công thức: `min(max(1·2^(attempt−1) + jitter, retry_after or 0), 120)`. Đã chạy thử: jitter 0.5 → attempt 1..4 = `1.5, 2.5, 4.5, 8.5`; `retry_after=10` ở attempt 2 → `10.0`; attempt 8 → `120.0` (trần).
- **Đọc `Retry-After`:** từ header HTTP hoặc từ `google.rpc.RetryInfo.retryDelay` (ví dụ `"7s"`):
@@SNIP src/knowledge_assistant/infrastructure/gemini_retry.py 67-82@@
  `re.fullmatch(r"(\d+(?:\.\d+)?)s", str(delay)) if delay else None` là biểu thức điều kiện; kết quả `None` nghĩa là không có gợi ý. Đã chạy thử: `api_error(429, retry_delay="7s")` → `retry_after_s = 7.0`.
- **C# analogy:** Polly `WaitAndRetryAsync` với `sleepDurationProvider` + jitter.
- **Tại sao:** đây là mẫu chuẩn cho API công cộng. Ở đây jitter được **inject** (`jitter=random.random`) nên test dùng giá trị cố định.
- **Pitfalls `[GENERAL]`:** retry mù không phân biệt lỗi (400) sẽ đốt quota; luôn phân loại trước.

### 2.3 Phân loại lỗi: `classify_failure`
- **Ý tưởng:** một hàm **duy nhất** biết exception nào của `google.genai`/`httpx` là lỗi nhà cung cấp; trả về object `Failure` (kind, retryable, reason, daily_quota_id, retry_after_s…), hoặc `None` nếu **không phải** lỗi provider (nghĩa là bug — người gọi **không được nuốt**).
@@SNIP src/knowledge_assistant/infrastructure/gemini_retry.py 111-123@@
@@SNIP src/knowledge_assistant/infrastructure/gemini_retry.py 125-149@@
- **Đọc chậm:** (1) `kind = "quota" if code == 429 else "unavailable" if code >= 500 else "other"` là **chuỗi biểu thức điều kiện** kết hợp; (2) `retryable = code in RETRYABLE_STATUS and daily is None` — 429 theo **ngày** không retry; (3) `reason` chỉ chứa mã và tên trạng thái, **không có thân lỗi** nên an toàn để log; thân lỗi (`body`) đã `redact_key`.
- **Đã chạy thử offline** (dùng `api_error` của `tests/fakes.py`): `503` → `unavailable`, retryable; `429` thường → `quota`, retryable; `429` kèm `QuotaFailure` có `...PerDay...` → `quota`, **không** retryable, `daily_quota_id` có giá trị; `400` → `other`, không retryable; `502` → `unavailable`, retryable; `TimeoutError` → `unavailable`, `ConnectionError` → `connection_error=True`; `ValueError` → `None`.
- **Tại sao:** tập trung phân loại ở một chỗ để embedder và LLM adapter **retry giống hệt nhau**.
- **Pitfalls `[REAL]`:** phát hiện 429 theo ngày dựa trên **hình dạng lỗi trong tài liệu**; docstring ghi "not yet seen in a real response". Cả 158 request của lượt đánh giá thật đều không gặp 429/5xx nào. [REPO src/knowledge_assistant/infrastructure/gemini_retry.py:85-90], [REPO docs/reports/epics/EPIC-05-evaluation.md:27-28]

### 2.4 Vòng `generate()`: retry, rồi fallback đúng một lần
@@SNIP src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py 140-161@@
Đọc: `for attempt in range(1, max_attempts + 1)`; thành công thì `return`; nếu **không retryable** hoặc **đã hết lượt** thì `break`; còn lại tính `wait`, tăng bộ đếm, log cảnh báo, `sleep(wait)`. Sau vòng lặp:
@@SNIP src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py 163-175@@
- **Đọc điều kiện fallback:** `failed.failure.kind != "other"` (lỗi 400… **không** fallback) **và** `settings.allow_fallback` **và** model dự phòng khác model chính. Fallback có **ngân sách output riêng** (`max(request.max_output_tokens, 2048)`), vì model dự phòng có "thinking".
- **Đã chạy thử offline** (jitter cố định 0.5, `sleep` là bộ ghi; script `learning/_tools/exercises/llm_retry_scenarios.py`):
  | Kịch bản | Model được gọi (theo thứ tự) | Đã "ngủ" (s) | Kết quả |
  |---|---|---|---|
  | A) 503, 503, rồi thành công | lite, lite, lite | 1.5, 2.5 | `gemini-3.5-flash-lite`, retries=2, fallback=False |
  | B) 503 ×3, fallback thành công | lite×3, flash | 1.5, 2.5 | `gemini-3.5-flash`, retries=2, fallback=True |
  | C) 503 ×3, fallback cũng 503 | lite×3, flash | 1.5, 2.5 | `LLMUnavailableError` (kind `unavailable`) |
  | D) 429 theo ngày | lite, flash | — | `gemini-3.5-flash`, retries=0, fallback=True |
  | E) 400 | lite | — | `LLMRequestError` (kind `other`), **không** fallback |
  | F) 503 ×3, **fallback tắt** | lite×3 | 1.5, 2.5 | `LLMUnavailableError` |
  Tổng thời gian chờ ở A = 4.0 s (`retry_wait_ms = 4000.0`).
- **Tại sao "một" lần fallback:** RPD của model dự phòng chỉ 20, nó là lưới an toàn, không phải đường chính. [REPO docs/architecture/decisions/0004-gemini-model-selection.md:79]
- **Tại sao evaluation tắt fallback (`ALLOW_FALLBACK=false`):** để **mọi** câu trả lời và mọi phán quyết đều từ `gemini-3.5-flash-lite`, không trộn model; case lỗi được ghi lỗi và chạy lại sau. [REPO docs/architecture/decisions/0004-gemini-model-selection.md:81] Nếu một câu trả lời vẫn đến từ model khác thì đó là bug — `ModelPurityError`. [REPO src/knowledge_assistant/core/exceptions/__init__.py:102-103]
- **Pitfalls:** `[GENERAL]` retry + fallback có thể che lỗi; repo ghi **`retry_count`, `fallback_used`, `model_used`** trên mọi câu trả lời và báo cáo độ trễ **tách** các trường hợp retry/fallback khỏi bảng chính. [REPO src/knowledge_assistant/application/evaluation/metrics/latency.py:1-11]

### 2.5 Một lần thử (`_attempt`) và bảo vệ hook quan sát
@@SNIP src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py 184-202@@
- **Ý tưởng:** `except PROVIDER_ERRORS as error` bắt **tuple** các class lỗi; phân loại; ghi thân của **429 đầu tiên** (một lần mỗi instance); gọi hook `on_provider_error` **trong `try/except` riêng** — hook hỏng chỉ bị log, không đổi retry/fallback/lỗi cuối.
- **Sự cố `[REAL]`:** bản đầu của hook **không** được bảo vệ: một hook ném exception sẽ kết thúc vòng retry sớm. Verifier (EVAL-003a) bắt được, sửa bằng guard, chứng minh bằng kịch bản 6 chuỗi lỗi và một mutation test. [REPO AI_WORKLOG.md:829-831]
- **Tại sao có hook:** để giữ lại **thân lỗi thật đầu tiên** của 429/5xx trong một lượt đánh giá (bằng chứng cho câu hỏi mở: chưa từng thấy 429/503 thật trên đường LLM). [REPO src/knowledge_assistant/infrastructure/llm/gemini/provider_error_log.py:1-9]

### 2.6 Kiểm tra phản hồi: `finish_reason`, rỗng, cắt cụt
@@SNIP src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py 204-221@@
@@SNIP src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py 222-231@@
- **Đọc:** `MAX_TOKENS` (câu trả lời bị cắt do hết hạn mức output) và các lý do dừng sớm (`SAFETY`, `RECITATION`…), hoặc văn bản rỗng → **`GenerationError`** (kèm `raw_text`); **không retry và không fallback** ("Unusable model output stays a GenerationError"). Message nêu tên model, giới hạn và usage để dễ chẩn đoán.
- **Tại sao:** một câu trả lời cụt là dữ liệu hỏng; không được biến thành "insufficient" hay coi như hợp lệ.

### 2.7 Dựng lỗi cuối cùng: mô tả lỗi của **model chính**
@@SNIP src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py 245-264@@
- **Ý tưởng:** message nói: "quota theo ngày đã hết, hãy tiếp tục sau khi reset 14:00 UTC+7" hoặc "rate limit… dai dẳng sau N lần" hoặc "service unavailable…". Nếu fallback cũng lỗi thì message nêu cả nó; nếu fallback tắt thì nói "the fallback model is off (ALLOW_FALLBACK=false)".
- Đoạn cuối chọn class lỗi và gắn nguyên nhân:
@@SNIP src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py 265-279@@
  `error.__cause__ = failed.error` gán chuỗi nguyên nhân thủ công (tương đương `raise ... from ...` nhưng ở đây lỗi được **trả về** rồi để người gọi `raise`).
- **Tại sao mô tả lỗi của model chính khi cả hai đều hỏng:** "a daily-quota primary whose fallback returns 503 is still a quota error (retrying will not help before the reset)". [REPO docs/architecture/decisions/0004-gemini-model-selection.md:105]

### 2.8 Timeout của mỗi lời gọi HTTP
- **Ý tưởng:** một lời gọi API có thể **treo**. Client Gemini được tạo lười, lần đầu cần dùng, với `HttpOptions(timeout=...)` tính bằng **mili-giây**: cấu hình lưu `timeout_s` (giây) nên đổi bằng `int(timeout_s * 1000)`.
@@SNIP src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py 130-138@@
- **Đọc chậm:** `if self._client is None:` là **khởi tạo lười (lazy)**; không có khoá thì ném `ConfigurationError` **trước** khi tạo client (test biên giới kiểm điều này: file 14 §2.3); `types.HttpOptions(timeout=...)` là cách SDK nhận timeout. Embedder dùng cùng cách ở [REPO src/knowledge_assistant/infrastructure/embeddings/gemini_embedder.py:115-115].
- **Liên hệ với phân loại lỗi (§1.4, §2.3):** một timeout là lỗi **`unavailable`** và **được retry**; nó khác "lỗi kết nối" (`connection_error=True`) ở chỗ có thể đã tới server. [REPO src/knowledge_assistant/infrastructure/gemini_retry.py:31-31]
- **C# analogy:** `HttpClient.Timeout` (mặc định 100 giây) hoặc `CancellationTokenSource(timeout)`.
- **Pitfalls `[GENERAL]`:** timeout **quá ngắn** biến lời gọi chậm-nhưng-thành-công thành lỗi (và đốt quota vì retry); **quá dài** làm GUI/tiến trình treo. Giá trị cụ thể nằm trong cấu hình; tôi không kiểm được mặc định đó có hợp lý với độ trễ thật (báo cáo ghi p95 `generate` ≈ 37–39s ở một vài lời gọi rất chậm, xem file 12 §2.3).

---

## Level 3 — Advanced

### 3.1 Che API key ở mọi đường ra
- **Trong code:**
@@SNIP src/knowledge_assistant/infrastructure/gemini_retry.py 52-57@@
  Thay **key đang cấu hình** và mọi chuỗi có **hình dạng** key Google (`AIza` + 35 ký tự) bằng `[REDACTED]`. Áp dụng ở: thân lỗi (`redact_key(raw_body(error))`), message lỗi cuối, và **mọi dòng** ghi vào file kết quả (`JsonlRecordStore` gọi `redact`). [REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:34,72]
- **Tại sao:** CLAUDE.md rule 7: "MUST NOT hard-code, commit, print or log keys". Key chỉ đọc từ biến môi trường (`get_gemini_api_key`). [REPO src/knowledge_assistant/config.py:33-35]
- **Pitfalls:** `[GENERAL]` che theo **mẫu** bổ sung cho che theo **giá trị**: bắt được cả key lạ chưa cấu hình. **Không** bao giờ in/ghi biến môi trường; repo tuân thủ (`.env` git-ignored, `.env.example` chỉ placeholder).

### 3.2 Quota theo ngày và múi giờ
- **Ý tưởng:** RPD reset lúc **nửa đêm giờ Pacific** (ADR-0004: "RPD resets at midnight Pacific"). Repo đặt hằng `DAILY_RESET = "14:00 UTC+7"` cho người dùng ở UTC+7 và chia kế hoạch quota theo mốc này. [REPO src/knowledge_assistant/infrastructure/gemini_retry.py:19], [REPO docs/architecture/decisions/0004-gemini-model-selection.md:27]
- **Xác nhận từ chủ dự án (bổ sung sau, 30/09/2026):** hạn ngạch hằng ngày reset lúc **nửa đêm giờ Pacific** = **14:00 UTC+7 khi Pacific ở giờ mùa hè (PDT, UTC−7)** và **15:00 UTC+7 khi ở giờ mùa đông (PST, UTC−8)**. Nguồn: quan sát của chủ dự án + tài liệu Google AI Studio (phần tài liệu này là `[GENERAL]`, tôi không tự kiểm được). Lưu ý của chủ dự án: **biểu đồ usage trong AI Studio chia ngày theo UTC−8**, nên biểu đồ có thể lệch một giờ so với mốc reset thật vào mùa hè. Hệ quả: hằng `DAILY_RESET = "14:00 UTC+7"` chỉ đúng nửa năm (PDT); đây là một ví dụ về **hard-code múi giờ**. Hệ thống dùng nó chỉ trong thông điệp và kế hoạch, không để quyết định logic retry.
- **Ở đâu quan trọng:** kế hoạch embedding chia hai ngày quota; kiểm tra `daily_quota_id` để không retry vô ích. [REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:85-99]
- **Pitfalls:** `[GENERAL]` luôn lưu và so sánh thời gian ở **UTC** trong code; chuyển sang múi giờ người dùng chỉ khi hiển thị. Repo ghi mốc thời gian có múi giờ (`+0700`) trong báo cáo và dùng `datetime.now(timezone.utc)` trong code ([REPO src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:90]).

### 3.3 Retry set là một quyết định, không phải một sự thật — vụ HTTP 502
- **Sự việc `[REAL]`:** bộ retry ban đầu của RAG-003 không retry 502, lệch danh sách của owner; verifier ghi là **F1** ("502 not retried"). Owner quyết định **thêm 502** vào tập chung (27/09/2026, ghi trong ADR-0004 amendment), nên 502 được retry như 503 — và điều này **đổi cả hành vi của embedder** (trước đó chỉ retry 429/500/503/504). [REPO docs/architecture/decisions/0004-gemini-model-selection.md:103]
- **Bằng chứng đã kiểm:** commit `7e192d4` "RAG-003 verify fixes: 502 retried, fallback output budget, --json schema documented" (tìm bằng `git log -S"502"` trên `gemini_retry.py`); re-verify của commit sửa cho kết quả **ACCEPT**. [REPO docs/reviews/code/RAG-003-verify.md:155,160-164] Mã hiện tại: `RETRYABLE_STATUS = {429, 500, 502, 503, 504}` ([REPO src/knowledge_assistant/infrastructure/gemini_retry.py:16]); đã chạy thử `classify_failure(api_error(502))` → `unavailable`, `retryable=True`.
- **Một mâu thuẫn trong tài liệu `[REAL]` (nhỏ):** `AI_WORKLOG.md:826-828` vẫn mô tả F1 như "an accepted, disclosed gap rather than silently left in the report", trong khi commit `7e192d4` và ADR cho thấy 502 **đã được sửa**. Đoạn worklog vì thế lỗi thời (hoặc mô tả trạng thái ngay lúc verify). Nguồn chính là ADR + code + commit.
- **Bài học:** một tham số nhỏ (tập mã HTTP retry) là **quyết định có chủ**, cần ghi ai quyết, khi nào, và test từng mã (ADR: "Each status 500, 502, 503, 504 has its own test for both adapters"). Và: tài liệu tổng hợp (worklog) có thể tụt hậu so với code — đối chiếu nhiều nguồn.

### 3.4 Chi phí: ước lượng mà không bịa số
- **Trong code:**
@@SNIP src/knowledge_assistant/application/evaluation/scoring.py 304-317@@
  Chi phí = `(prompt × giá_vào + (output + thinking) × giá_ra) / 1 000 000`. Nếu giá của model là `null` hoặc các lần gọi trộn nhiều model → trả `usd: None` kèm **lý do**, **không đoán**. `config/pricing.json` ghi giá gói trả phí cho `gemini-3.5-flash-lite` (vào 0.30$, ra 2.50$ mỗi 1M token, output đã gồm thinking), còn giá của `gemini-3.5-flash` và embedding là `null` ("never a guess"). [REPO config/pricing.json:1-28]
- **Đã chạy thử:** 100 lần gọi, 120 000 prompt token, 10 000 output token, 0 thinking → `usd = (120000×0.30 + 10000×2.50)/1e6 = 0.061`; với `gemini-3.5-flash` → `usd None`, "price … not available"; với hai model → `usd None`, "need exactly one priced model".
- **Tại sao:** các lần chạy thật dùng free tier và **không tính tiền**; số ước lượng có ghi chú rõ ("estimate: list price per 1M tokens; the runs used the free tier and were not billed").
- **Pitfalls:** `[GENERAL]` thiếu số thinking token bị tính 0 và **có ghi chú** số lần gọi thiếu ("counted as 0") — không giấu.

### 3.5 Lập ngân sách một lượt đánh giá thật
- Một lượt đánh giá (cả hai arm, full, split eval) tốn ~**122 request LLM + 36 request embedding** cộng judge; kết quả thật: **0** lỗi 429/5xx qua ~158 request. [REPO README.md:146], [REPO docs/reports/epics/EPIC-05-evaluation.md:27-28]
- **Runner đếm ngân sách LLM (kể cả retry) trước mỗi case;** gặp lỗi quota thì ghi lỗi **một case** và dừng, để resume sau; lỗi provider khác ghi rồi chạy tiếp; bug thì dừng cả run. [REPO src/knowledge_assistant/application/evaluation/run_evaluation.py:10-13]
- **Tại sao:** ngân sách ngày (500 RPD) chia cho answer + judge + fallback; vượt là dừng, không mất dữ liệu đã có.

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** Model chính có RPM = 15 nhưng throttle mặc định = 13. Vì sao không đặt 15?
<details><summary>Đáp án</summary>
Để không bao giờ chạm giới hạn của nhà cung cấp ("so a run never trips the provider limit"): độ trễ mạng và sai lệch đồng hồ có thể làm hai lời gọi rơi vào cùng phút của phía server ([REPO src/knowledge_assistant/config.py:74-78]).
</details>

**B2 (Basic).** Trong các mã HTTP sau, mã nào **được retry**: 400, 429 (theo phút), 429 (theo ngày), 500, 502, 503, 504, 404?
<details><summary>Đáp án</summary>
Retry: 429 theo phút, 500, 502, 503, 504 (và timeout/lỗi kết nối). Không retry: 400, 404, và 429 **theo ngày** ([REPO src/knowledge_assistant/infrastructure/gemini_retry.py:16,133]). Đã chạy thử `classify_failure`.
</details>

**B3 (Basic).** `retry_count` có tính lần gọi fallback không?
<details><summary>Đáp án</summary>
Không: `retry_count` chỉ đếm retry trên model chính (0..max_attempts−1); lần gọi fallback không phải retry mà đặt `fallback_used=True` và `model_used` = model dự phòng ([REPO src/knowledge_assistant/core/interfaces/llm.py:15-19]). Kịch bản B: `retries=2, fallback=True`.
</details>

**I1 (Intermediate).** Tính tay `backoff_wait_s(1, 7.0, 0.5)`, `backoff_wait_s(3, 2.0, 0.0)` và `backoff_wait_s(3, None, 0.9)`.
<details><summary>Đáp án</summary>
`max(1·2⁰+0.5=1.5, 7.0) = 7.0`; `max(1·2²+0=4.0, 2.0) = 4.0`; `4.9`. Công thức: `min(max(1·2^(attempt−1)+jitter, retry_after or 0), 120)` ([REPO src/knowledge_assistant/infrastructure/gemini_retry.py:104-108]).
</details>

**I2 (Intermediate).** Chạy `learning/_tools/exercises/llm_retry_scenarios.py` (xem đầu file cách đặt `PYTHONPATH`). Không nhìn bảng ở 2.4, dự đoán kết quả kịch bản D và F trước, rồi so sánh. Sau đó dự đoán kịch bản **G** (đã có trong script): ba lỗi 429 **theo phút** (không có `quota_id`) rồi fallback thành công.
<details><summary>Đáp án</summary>
D: gọi `lite` rồi `flash`, không ngủ; F: gọi `lite` ×3, ngủ 1.5 rồi 2.5, ném `LLMUnavailableError` (kind `unavailable`) vì fallback tắt. G (429 theo **phút**, không có `quota_id`): `retryable=True` nên 3 lần `lite` với ngủ 1.5 và 2.5, rồi fallback `flash` thành công → `model_used="gemini-3.5-flash"`, `retries=2`, `fallback=True` (kết quả đã được chạy thật trong script).
</details>

**I3 (Intermediate).** Chi phí: 250 lần gọi, 300 000 prompt token, 25 000 output token, 0 thinking, model `gemini-3.5-flash-lite`. Dùng công thức và giá trong `config/pricing.json`.
<details><summary>Đáp án</summary>
`(300000 × 0.30 + 25000 × 2.50) / 1e6 = (90000 + 62500)/1e6 = 0.1525` USD (ước lượng giá niêm yết; free tier thực tế **không** bị tính tiền). Kèm ghi chú số lần gọi thiếu thinking-token nếu có ([REPO src/knowledge_assistant/application/evaluation/scoring.py:304-317]).
</details>

**A1 (Advanced).** Vì sao `GenerationError` (MAX_TOKENS/JSON hỏng) **không** kích hoạt fallback, trong khi 503 thì có?
<details><summary>Đáp án</summary>
503 là lỗi tạm của **dịch vụ** — model khác có thể phục vụ được. `GenerationError` là **đầu ra không dùng được** của chính prompt/ngân sách; gọi lại (hoặc đổi model) không đảm bảo sửa và tốn quota khan hiếm của fallback (RPD 20). Đồng thời luật dự án cấm biến lỗi thành "insufficient" ([REPO docs/architecture/decisions/0004-gemini-model-selection.md:107], [REPO src/knowledge_assistant/application/generation/answer_question.py:1-9]).
</details>

**A2 (Advanced).** Thiết kế test (giấy) chứng minh "hook ném lỗi không làm đổi kết quả retry". Cần fake gì, khẳng định gì?
<details><summary>Đáp án</summary>
Dùng client giả kịch bản `[503, 503, "ok"]`, `on_provider_error` là hàm luôn `raise RuntimeError`; khẳng định: `generate()` vẫn trả thành công sau đúng 3 lần gọi, `retry_count == 2`, các thời gian ngủ `[1.5, 2.5]`, và cảnh báo "provider-error hook failed" được log. Đây đúng là hướng của bản sửa (guard `try/except Exception` ở [REPO src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py:196-200]) và mutation test đã kiểm ([REPO AI_WORKLOG.md:829-831]).
</details>

**A3 (Advanced).** Nếu một dịch vụ trả 429 với `Retry-After: 300` (5 phút), `backoff_wait_s(1, 300.0, jitter)` là bao nhiêu và điều đó nói gì về thiết kế?
<details><summary>Đáp án</summary>
`min(max(1+jitter, 300), 120) = 120.0`: một lần chờ **không bao giờ** vượt 120 s, dù server yêu cầu 300 s. Thiết kế ưu tiên "không treo im lặng"; đánh đổi là có thể retry sớm hơn server muốn và lại bị 429. Với lỗi quota kéo dài, lượt thử cuối sẽ ném `LLMQuotaError` và người dùng quyết định ([REPO src/knowledge_assistant/infrastructure/gemini_retry.py:18]).
</details>

## Self-check questions
1. RPM, TPM, RPD khác nhau ra sao; cái nào adapter ép?
2. Vì sao cần jitter? Trần 120 giây để làm gì?
3. Mọi lỗi API được phân thành ba `kind` nào và mỗi kind có retry không?
4. Khi nào `generate()` gọi fallback? Khi nào **không**?
5. Vì sao evaluation tắt fallback?
6. `latency_ms` khác `retry_wait_ms` và `throttle_wait_ms` thế nào?
7. Vì sao "None" ≠ 0 với token count?

## Interview Q&A
1. **"Bạn thiết kế retry cho API có rate limit thế nào?"** — Phân loại lỗi, retry backoff luỹ thừa + jitter + `Retry-After`, trần thời gian, giới hạn số lần, fallback một lần, throttle chủ động phía client ([REPO src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py:6-20]).
2. **"Tại sao không retry mọi lỗi?"** — 400/401/403/404 không tự hết; gửi lại đốt quota. Chỉ retry lỗi có thể tạm thời ([REPO src/knowledge_assistant/infrastructure/gemini_retry.py:16]).
3. **"Làm sao đảm bảo kết quả đánh giá không trộn model?"** — `ALLOW_FALLBACK=false` + kiểm tra "model purity" (fallback/model khác = bug, ghi log và dừng) ([REPO src/knowledge_assistant/application/evaluation/run_evaluation.py:9-10]).
4. **"Bạn ngăn rò rỉ API key thế nào?"** — Chỉ đọc từ env, `redact_key` che theo giá trị và theo mẫu, mọi dòng ghi file đi qua `redact` ([REPO src/knowledge_assistant/infrastructure/gemini_retry.py:52-57]).
5. **"Kể một sai lầm về retry đã được bắt."** — Hook quan sát không được bảo vệ làm vòng retry kết thúc sớm (EVAL-003a F1); 502 không nằm trong tập retry (RAG-003 F1) ([REPO AI_WORKLOG.md:826-831]).
6. **"Ước tính chi phí thế nào khi thiếu số liệu?"** — Trả `None` kèm lý do; giá `null` không bao giờ được đoán ([REPO config/pricing.json:1-28]).

## Further reading
- Google AI for Developers: *Gemini API — Rate limits*, *Error codes* (tài liệu chính thức; các số có thể đổi). `[GENERAL]`
- AWS Architecture Blog, *Exponential Backoff and Jitter* (bài kinh điển về jitter). `[GENERAL]`
- Polly (.NET) docs — *Retry*, *Rate limiter*, *Fallback* (tương đương khái niệm với code ở đây). `[GENERAL]`
- Tiếp theo: [10](10-evaluation-design.md) (thiết kế đánh giá) và [08](08-generation-and-prompting.md) (prompt và sinh câu trả lời).
