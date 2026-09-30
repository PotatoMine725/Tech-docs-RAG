# Interview bank — câu hỏi phỏng vấn gom từ các file học
> Commit: 762b754 (tag `v1.0-submission`) · File này được **sinh tự động** từ mục *Interview Q&A* của từng file (`_tools/build_interview_bank.py`); không có nội dung mới. Mỗi câu trả lời dẫn `[REPO path:line]` để bạn kiểm chứng; hãy luyện trả lời **bằng lời của bạn**, không học thuộc.

> Tổng số câu: **95**.


## [01](01-python-for-csharp-devs.md) — 01 · Python cho dev C#: cú pháp và idiom có thật trong repo này

1. **"Python type hints có được ép lúc chạy không?"** — Không. Trong repo, nơi cần bảo đảm kiểu (output của LLM), code tự kiểm tra bằng `isinstance` ([REPO src/knowledge_assistant/application/generation/answer_question.py:36-56]).
2. **"Structural typing là gì, dùng ở đâu?"** — Class thoả `Protocol` nếu có đúng method; repo dùng để core định nghĩa cổng (`LLM`, `Embedder`, `VectorStore`) mà adapter không cần kế thừa ([REPO src/knowledge_assistant/core/interfaces/llm.py:36-37]).
3. **"Vì sao inject clock/sleep?"** — Để test code phụ thuộc thời gian chạy tức thì và xác định ([REPO src/knowledge_assistant/infrastructure/embeddings/throttle.py:24-31]).
4. **"Khi nào bắt `except Exception`?"** — Chỉ ở ranh giới, có lý do và log; ví dụ hook quan sát không được làm đổi hành vi retry ([REPO src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py:196-200]).
5. **"Dataclass frozen giải quyết gì?"** — Dữ liệu chảy giữa layer bất biến, có equality theo giá trị, ≈ `record` C#.


## [01b](01b-python-code-reading-guide.md) — 01b · Hướng dẫn đọc hiểu code Python (bảng giải mã + template)

1. **"Bạn đọc code Python lạ như thế nào?"** — Docstring → import → hằng số/kiểu → hàm công khai → chạy bằng đầu một ví dụ nhỏ; dùng test làm ví dụ sống.
2. **"Decorator là gì?"** — Hàm nhận hàm và trả hàm; repo dùng decorator chuẩn như `@dataclass`, `@property`, `@contextmanager`, `@pytest.fixture` (mục T9).
3. **"Khác biệt `is None` và `== None`?"** — `is` so sánh danh tính, là cách chuẩn với `None` ([REPO src/knowledge_assistant/presentation/desktop/viewmodels/ask_viewmodel.py:105]).
4. **"Vì sao test dùng fake thay vì gọi API thật?"** — Xác định, miễn phí, không cần mạng/key; repo có `FakeEmbedder`, `FakeClock`, `FakeLLM`... ([REPO tests/fakes.py:12-62]).


## [02](02-python-tooling-and-dependencies.md) — 02 · Công cụ Python và quản lý phụ thuộc: venv, pip, `pyproject.toml`, src layout, import, biến môi trường, cấu hình pytest

1. **"Virtual environment dùng để làm gì?"** — Cô lập phụ thuộc theo dự án để tái lập và tránh xung đột phiên bản ([REPO README.md:107-114]).
2. **"Bạn đảm bảo test không gọi API thật thế nào?"** — Marker `gemini` + `addopts = "-m 'not gemini'"` + fake cho mọi adapter; adapter Gemini không có key thì ném lỗi cấu hình và không gọi mạng ([REPO pyproject.toml:25-31]).
3. **"Bạn quản lý cấu hình và bí mật ra sao?"** — Biến môi trường (`os.getenv`), `.env` git-ignored, `.env.example` chỉ placeholder; key chỉ đọc từ môi trường và không bao giờ in ([REPO src/knowledge_assistant/config.py:33-35]).
4. **"Tại sao dùng src layout?"** — Tránh import nhầm bản chưa cài từ thư mục hiện tại; buộc đi qua cơ chế cài/`sys.path` có chủ đích ([REPO pyproject.toml:22-23]).
5. **"Một lỗi môi trường bạn từng gặp?"** — `pip install -r requirements.txt` không đủ (thiếu editable install) — bắt được ở test clone sạch của QC-001; và worktree dùng chung `.venv` chạy nhầm code checkout chính ([REPO README.md:116-120]).
6. **"Đường dẫn tương đối theo cwd có vấn đề gì?"** — Chạy từ thư mục khác ghi/đọc sai chỗ; repo neo đường dẫn vào `PROJECT_ROOT` ([REPO src/knowledge_assistant/config.py:7-15]).


## [03](03-architecture-and-gui.md) — 03 · Kiến trúc phân lớp, ports & adapters, composition root, và GUI (PySide6 MVVM + thread)

1. **"Clean architecture ở dự án này khác project reference của .NET ở điểm nào?"** — Không có compiler ép; luật được canh bằng test `ast` ([REPO tests/unit/test_project_structure.py:11-19]).
2. **"Kể một lần thiết kế port bị rò rỉ chi tiết công nghệ?"** — `plan_calls` (batching của Gemini) nằm trong `Embedder` core; ADR-0005 Amendment 2 chuyển sang `PlannedEmbedder` ([REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:123]).
3. **"Làm thế nào test được code gọi LLM mà không tốn quota?"** — `LLM` là `Protocol`; test truyền `FakeLLM`/`ScriptedLLM` ([REPO tests/fakes.py:187]).
4. **"MVVM ở đây khác WPF thế nào?"** — Không có data binding: view-model phát `_notify()` tới listener; view vẽ lại. Đổi lại, view-model test được không cần Qt.
5. **"Vì sao dùng `Lock` trong `CoreAskQuestion._service`?"** — Service theo arm dựng lười trên worker thread; lock chặn dựng hai lần ([REPO src/knowledge_assistant/presentation/desktop/viewmodels/core_ask_question.py:60-64]).


## [04](04-data-io-and-reliability-patterns.md) — 04 · Dữ liệu vào/ra và các mẫu độ bền: JSONL, append-only, hash, cache, idempotent, resume, tính xác định

1. **"Bạn thiết kế pipeline dài có thể dừng và chạy tiếp thế nào?"** — Ghi từng dòng bền vững, khoá bằng hash/`chunk_id`, chỉ xử lý phần còn thiếu, manifest cấu hình và từ chối resume khi thiết lập đổi ([REPO src/knowledge_assistant/application/evaluation/run_evaluation.py:1-13]).
2. **"Làm sao ghi file an toàn khi mất điện?"** — Append từng dòng + `fsync` (chịu được dòng cụt); file nhỏ ghi nguyên tử bằng tmp + `os.replace` ([REPO src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py:32-40]).
3. **"Cache khoá theo gì?"** — Hash của (model, task, text) để tránh dùng nhầm vector; lưu float32 BLOB; commit theo từng lời gọi để không mất tiền đã trả ([REPO src/knowledge_assistant/infrastructure/persistence/embedding_cache.py:1-6]).
4. **"Idempotency là gì và làm sao đạt được?"** — Chạy nhiều lần = chạy một lần; đạt bằng khoá danh tính xác định (`chunk_id`) và kiểm "đã có chưa" trước khi làm ([REPO src/knowledge_assistant/application/ingestion/index_corpus.py:71-77]).
5. **"Kể một lỗi thật về xuống dòng."** — Test Windows fail vì `write_text` không có `newline="\n"`; và hash phải tính lại theo LF; dự án ép LF bằng `.gitattributes` ([REPO docs/reports/execution/INGEST-003.md:66], [REPO .gitattributes:1-3]).
6. **"Nguồn không xác định trong hệ thống của bạn là gì?"** — HNSW (test flaky), đầu ra LLM dù temperature 0, độ trễ; được cô lập ở biên và ghi nhận ([REPO docs/specs/generation-spec.md:30-32]).


## [05](05-rag-fundamentals.md) — 05 · RAG cơ bản: toàn bộ pipeline của repo, từng chặng một

1. **"Giải thích RAG bằng ví dụ từ dự án của bạn."** — Câu hỏi được embed, tìm top-5 đoạn trong Chroma, đưa vào prompt cùng luật "chỉ dùng CONTEXT"; LLM trả JSON có `answer`, `cited_passages`, `insufficient` ([REPO config/prompts/answer_v2.md:1-13]).
2. **"Làm thế nào bạn giảm hallucination?"** — Prompt ép dùng context; gate ngăn LLM chạy khi retrieval yếu; citation kiểm được; đánh giá có nhãn `hallucination` và judge kiểm chứng ([REPO src/knowledge_assistant/application/evaluation/metrics/mapping.py:3-12]).
3. **"Tại sao có hai lớp từ chối?"** — Gate rẻ (không tốn LLM) nhưng thô; lớp LLM tinh nhưng tốn request ([REPO src/knowledge_assistant/application/generation/answer_question.py:1-9]).
4. **"Làm sao index resume được?"** — `pending()` chỉ lấy chunk chưa có trong store; cache SQLite giữ vector đã trả tiền ([REPO src/knowledge_assistant/application/ingestion/index_corpus.py:71-77]).
5. **"Giới hạn của pipeline này?"** — Không rerank/hybrid; ngưỡng tune trên n nhỏ; nhận diện ngôn ngữ bằng heuristic ([REPO README.md:245]).


## [06](06-embeddings-and-vector-search.md) — 06 · Embeddings và tìm kiếm vector (ChromaDB)

1. **"Cosine similarity là gì, vì sao dùng thay khoảng cách Euclid?"** — Đo góc, không đo độ dài; trên vector đơn vị xếp hạng như nhau, nhưng cosine vẫn đúng khi vector không chuẩn hoá ([REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:69]).
2. **"Bạn xử lý giới hạn quota của API embedding thế nào?"** — Đo (V-1), throttle cửa sổ trượt tính theo số text, batch ≤45 và nửa ngân sách token, cache SQLite commit từng cuộc gọi, chia hai ngày quota ([REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:41-46,85-99]).
3. **"Vector DB nhúng khác server thế nào?"** — Nhúng: chạy trong tiến trình, dữ liệu là thư mục; không có server để vận hành; đánh đổi là chia sẻ đa tiến trình/luồng hạn chế ([REPO src/knowledge_assistant/infrastructure/vector_store/chromadb/chroma_store.py:78]).
4. **"Kể một lỗi kiến trúc bạn phát hiện ở tầng embedding."** — Cache và embedder chia batch khác nhau → mất vector đã trả tiền khi lỗi (RAG-001a F1/F2), sửa bằng `plan_calls` ([REPO docs/architecture/decisions/0005-embedding-and-vector-store-settings.md:109-118]).
5. **"Bạn xử lý flaky test thế nào?"** — Chạy lại 15 lần, công khai không tái hiện, không xoá test ([REPO README.md:305-310]).


## [07](07-chunking-and-retrieval.md) — 07 · Chunking (Arm A vs Arm B), khử trùng, over-fetch và refusal gate

1. **"Bạn chọn kích thước chunk như thế nào?"** — Dựa trên phân phối đo được của corpus (không dựa kết quả retrieval), ghi trong ADR-0003 D3; mọi thay đổi phải qua ADR mới/amendment có bằng chứng ([REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:82]).
2. **"Header-aware chunking hơn gì fixed-size?"** — Không cắt code/bảng (3.27% vs 45.05% chunk cắt qua code), giữ ngữ cảnh heading; đổi lại phức tạp hơn và chunk không đều ([REPO docs/reports/execution/INGEST-004.md:44-52]).
3. **"Xử lý tài liệu trùng lặp thế nào?"** — Bỏ trùng `content_hash` lúc chunk (447 ở Arm A), và khử trùng theo `passage_hash` lúc retrieval với over-fetch ([REPO docs/specs/retrieval-spec.md:14-21]).
4. **"Làm sao quyết định ngưỡng từ chối?"** — Công thức trên dev, có bảng số; thừa nhận n nhỏ và chỉ tune trên Arm A ([REPO docs/specs/retrieval-spec.md:38-56]).
5. **"Một quyết định thiết kế có thể làm lệch thước đo — ví dụ?"** — Chunk chỉ chứa heading tạo hit giả cho Arm A; D3a loại bỏ, quyết định trước khi có kết quả ([REPO docs/architecture/decisions/0003-chunking-parameters-and-experiment.md:27-33]).


## [08](08-generation-and-prompting.md) — 08 · Sinh câu trả lời và prompt: template có phiên bản, structured output, luật từ chối, phân tích citation, prompt injection

1. **"Bạn ép LLM trả về dữ liệu có cấu trúc thế nào và tin nó tới đâu?"** — JSON mode + schema, **rồi kiểm lại kiểu ở phía mình**: JSON mode không đảm bảo ngữ nghĩa (`answer` rỗng, số passage ngoài phạm vi). Đầu ra hỏng ném `GenerationError` chứ không im lặng chấp nhận ([REPO src/knowledge_assistant/application/generation/answer_question.py:36-56]).
2. **"Bạn quản lý phiên bản prompt ra sao?"** — Prompt là file bất biến theo phiên bản, tên file là version, ghi vào từng kết quả; sửa = file mới, giữ bản cũ làm bằng chứng ([REPO docs/specs/generation-spec.md:20-24]).
3. **"Làm sao ngăn model bịa citation?"** — Đánh số passage; model chỉ được trích số 1..k; số ngoài phạm vi bị bỏ và ghi lại; excerpt là tiền tố nguyên văn nên kiểm được ([REPO src/knowledge_assistant/application/citation/citations.py:136-150]).
4. **"Kể một lỗi tương tác giữa prompt và parser."** — `args[0]` bị coi là citation; sửa cả hai phía: parser bỏ qua code, prompt v2 yêu cầu bọc backtick; kiểm bằng mutation (7 và 3 test fail khi tắt) ([REPO AI_WORKLOG.md:344-352]).
5. **"Bạn phân biệt 'không có câu trả lời' và 'hệ thống lỗi' thế nào?"** — Ba đường riêng: cổng truy xuất, `insufficient` của model (cả hai là kết quả hợp lệ), và `GenerationError`/`LLMError` (lỗi). Không bao giờ đổi lỗi thành insufficient ([REPO docs/specs/generation-spec.md:36-38]).
6. **"Prompt injection ảnh hưởng gì tới hệ thống này?"** — Corpus cố định nên hiện chưa phải rủi ro thực tế; repo nêu rõ đó là rủi ro của bản có upload và không có bộ lọc injection. Trả lời trung thực quan trọng hơn khoe phòng thủ không có ([REPO README.md:323-325]).


## [09](09-llm-api-engineering.md) — 09 · Kỹ thuật gọi LLM API: rate limit, throttle, retry/backoff, fallback, phân loại lỗi, token, chi phí

1. **"Bạn thiết kế retry cho API có rate limit thế nào?"** — Phân loại lỗi, retry backoff luỹ thừa + jitter + `Retry-After`, trần thời gian, giới hạn số lần, fallback một lần, throttle chủ động phía client ([REPO src/knowledge_assistant/infrastructure/llm/gemini/gemini_llm.py:6-20]).
2. **"Tại sao không retry mọi lỗi?"** — 400/401/403/404 không tự hết; gửi lại đốt quota. Chỉ retry lỗi có thể tạm thời ([REPO src/knowledge_assistant/infrastructure/gemini_retry.py:16]).
3. **"Làm sao đảm bảo kết quả đánh giá không trộn model?"** — `ALLOW_FALLBACK=false` + kiểm tra "model purity" (fallback/model khác = bug, ghi log và dừng) ([REPO src/knowledge_assistant/application/evaluation/run_evaluation.py:9-10]).
4. **"Bạn ngăn rò rỉ API key thế nào?"** — Chỉ đọc từ env, `redact_key` che theo giá trị và theo mẫu, mọi dòng ghi file đi qua `redact` ([REPO src/knowledge_assistant/infrastructure/gemini_retry.py:52-57]).
5. **"Kể một sai lầm về retry đã được bắt."** — Hook quan sát không được bảo vệ làm vòng retry kết thúc sớm (EVAL-003a F1); 502 không nằm trong tập retry (RAG-003 F1) ([REPO AI_WORKLOG.md:826-831]).
6. **"Ước tính chi phí thế nào khi thiếu số liệu?"** — Trả `None` kèm lý do; giá `null` không bao giờ được đoán ([REPO config/pricing.json:1-28]).


## [10](10-evaluation-design.md) — 10 · Thiết kế đánh giá: bộ câu hỏi eval-v1, đóng băng, tách dev/eval, luật hit, metric và mẫu số, tính hợp lệ

1. **"Bạn thiết kế bộ đánh giá cho hệ thống RAG thế nào?"** — Ground truth viết trước index; tách dev/eval; đóng băng bằng hash + tag; metric tách tầng (retrieval, câu trả lời, citation, latency); có nhóm song song cho ngôn ngữ; near-miss cho từ chối ([REPO docs/specs/evaluation-dataset-design.md:9-13]).
2. **"Làm sao tránh tự lừa mình khi đánh giá?"** — Freeze + hash + amendment log; báo cả lenient và strict; báo `n` cho mọi tỉ lệ; liệt kê threats to validity; không chỉnh trên eval ([REPO docs/specs/evaluation-spec.md:87-98]).
3. **"Recall@k và MRR khác nhau ra sao?"** — hit@k: có tìm được trong k không; MRR: tìm được sớm cỡ nào (`1/hạng`). Repo báo hit@1/3/5 + MRR ([REPO src/knowledge_assistant/application/evaluation/metrics/retrieval.py:27]).
4. **"Vì sao không cho LLM chọn nhãn cuối?"** — Nhãn phải xác định và kiểm thử được; judge chỉ cấp dữ liệu, bảng `map_result` quyết định ([REPO src/knowledge_assistant/application/evaluation/metrics/mapping.py:1-4]).
5. **"Một metric có mẫu số sai thì sao?"** — Đã xảy ra: câu văn spec sai về mẫu số, sửa ở verify; báo cáo luôn ghi `22/31` vs `23/32` và lý do ([REPO docs/reports/epics/EPIC-06-experiment.md:80-81]).
6. **"Bạn báo cáo kết quả không có ý nghĩa thống kê thế nào?"** — "Không có khác biệt đáng tin ở n = X", kèm CI và số cặp bất đồng, không tuyên bố arm nào hơn ([REPO docs/reports/epics/EPIC-06-experiment.md:82-83]).


## [11](11-llm-as-judge.md) — 11 · LLM-as-judge: prompt chấm điểm, judge chỉ cấp dữ liệu, parse chặt, cache, spot-check của người, Cohen's κ

1. **"Bạn dùng LLM-as-judge thế nào cho đáng tin?"** — Rubric ràng buộc nguồn; judge chỉ cấp dữ liệu, nhãn do code; parse nghiêm ngặt; cache khoá hash; spot-check mù bằng người + κ ([REPO src/knowledge_assistant/application/evaluation/judge.py:1-30]).
2. **"Judge và model trả lời là một — có vấn đề gì?"** — Self-preference; repo ghi nhận giới hạn và bù bằng spot-check, không tuyên bố loại bỏ được ([REPO docs/specs/evaluation-spec.md:69]).
3. **"Judge trả JSON sai thì làm gì?"** — `judge_error`, giữ raw text, thử lại một lần, rồi liệt kê record như chưa gắn nhãn; **không** đoán ([REPO src/knowledge_assistant/application/evaluation/judge.py:195-228]).
4. **"Cohen's κ dùng để làm gì?"** — Đo đồng thuận đã hiệu chỉnh cho ngẫu nhiên; ở đây 0.688 với 8/10 ([REPO docs/reports/epics/EPIC-05-evaluation.md:375-383]).
5. **"Bạn đổi prompt judge giữa chừng thì sao?"** — Hash khác → `JudgeCacheMismatch`; phải tăng version hoặc dùng thư mục mới ([REPO src/knowledge_assistant/application/evaluation/judge.py:308-320]).
6. **"Kể một lỗi thật của judge."** — `Q-EVAL-002:B`: judge chép source id `22` vào trường marker; parse chặt bắt được; record chưa gắn nhãn, được liệt kê ([REPO docs/reports/epics/EPIC-06-experiment.md:103-105]).


## [12](12-statistics-for-experiments.md) — 12 · Thống kê cho thí nghiệm: kiểm định ghép cặp, bootstrap, phân vị, luật diễn đạt, sức mạnh thống kê

1. **"McNemar test dùng khi nào?"** — So hai tỉ lệ nhị phân trên cùng một tập mẫu (ghép cặp); chỉ dùng các cặp bất đồng; bản exact dùng nhị thức, tốt cho n nhỏ ([REPO src/knowledge_assistant/application/evaluation/stats.py:34-46]).
2. **"Bootstrap là gì, khác t-test thế nào?"** — Giả lập phân phối của thống kê bằng lấy mẫu có hoàn lại, không cần giả định phân phối; ở đây lấy mẫu **chỉ số cặp**, 10 000 lần, seed 42 ([REPO src/knowledge_assistant/application/evaluation/stats.py:63-81]).
3. **"Bạn báo cáo kết quả không có ý nghĩa thế nào?"** — "No statistically reliable difference at n = X" kèm CI; không tuyên bố arm thắng ([REPO src/knowledge_assistant/application/evaluation/experiment.py:152-158]).
4. **"Vì sao tự cài Wilcoxon?"** — scipy không có trong môi trường; bản tự cài chính xác cả khi có hòa; bù lại có thể lệch nhẹ scipy ở ca hòa và điều đó được ghi ([REPO src/knowledge_assistant/application/evaluation/stats.py:117-120]).
5. **"Percentile p95 tính thế nào?"** — Nearest-rank `ceil(p/100 × n)` với số hữu tỉ chính xác, không nội suy ([REPO src/knowledge_assistant/application/evaluation/metrics/latency.py:19-27]).
6. **"Điều gì thống kê không cứu được trong thí nghiệm này?"** — Confounding do thứ tự chạy/cache, một lần chạy mỗi arm, ngưỡng chỉnh trên Arm A ([REPO docs/reports/epics/EPIC-06-experiment.md:85-122]).


## [13](13-case-study-exp-001.md) — 13 · Ca nghiên cứu EXP-001: Arm A vs Arm B từ giả thuyết đến kết luận trung thực

1. **"Kể về một thí nghiệm bạn thiết kế."** — Chỉ đổi chunker, mọi thứ khác giữ hằng và máy kiểm; bộ câu hỏi đóng băng; kiểm định ghép cặp; đọc từng ca ở mức chunk; kết luận đúng mức ([REPO docs/reports/epics/EPIC-06-experiment.md:17-21]).
2. **"Kết quả không có ý nghĩa thống kê thì bạn làm gì?"** — Nói rõ "không đủ bằng chứng", trình bày CI, và đào xuống cơ chế (chunk-level) để rút bài học thay vì bịa kết luận ([REPO docs/reports/epics/EPIC-06-experiment.md:556-571]).
3. **"Làm sao biết lỗi do hệ thống hay do cách đo?"** — Đọc từng ca bất đồng, đọc `reason` của judge, đối chiếu spot-check của người ([REPO docs/reports/epics/EPIC-06-experiment.md:534-554]).
4. **"Vì sao giữ Arm A khi accuracy B nhỉnh hơn?"** — Vì khác biệt accuracy không đáng tin; A rẻ hơn 494 token, giữ code nguyên, citation thẳng hàng section; lựa chọn dựa vào chi phí và cơ chế đo được ([REPO docs/reports/epics/EPIC-06-experiment.md:575-580]).
5. **"Cache ảnh hưởng thí nghiệm ra sao?"** — Tiết kiệm quota nhưng gây confounding độ trễ (`embed_query` B 0.1 ms vs A 352 ms), nên độ trễ không được kiểm định ([REPO docs/reports/epics/EPIC-06-experiment.md:113-118]).
6. **"Bạn đề xuất gì tiếp theo?"** — Ngưỡng theo từng arm, hybrid retrieval + đa dạng hoá biến thể, viết lại truy vấn VI→EN, mỗi cái kèm metric thành công định trước ([REPO docs/reports/epics/EPIC-06-experiment.md:586-603]).


## [14](14-testing-and-quality.md) — 14 · Kiểm thử và chất lượng: pytest, fake tự viết, bộ test offline, test không ổn định (flaky), mutation testing

1. **"Bạn kiểm thử code gọi API bên ngoài thế nào?"** — Đặt sau interface, dùng fake có kịch bản thất bại, tiêm đồng hồ/sleep; mặc định offline, test live tách bằng marker ([REPO pyproject.toml:25-31]).
2. **"Coverage 100% có đủ không?"** — Không; chỉ nói dòng nào được chạy. Mutation testing kiểm test có **bắt lỗi**; repo dùng như cổng nghiệm thu ([REPO AI_WORKLOG.md:351-352]).
3. **"Bạn xử lý test flaky ra sao?"** — Thu bằng chứng có hệ thống (15/15), không che giấu, ghi nhận nguyên nhân nghi ngờ nhưng chưa xác nhận ([REPO README.md:305-309]).
4. **"Làm sao test độ trễ/retry mà không chờ thật?"** — Đồng hồ giả trong đó `sleep` cộng thời gian ([REPO tests/fakes.py:50-62]).
5. **"Bạn giữ kiến trúc phân tầng thế nào?"** — Một test dùng `ast` quét import và fail nếu vi phạm ([REPO CLAUDE.md:7]).
6. **"Một sai lầm bạn từng gặp khi thử đột biến?"** — Khôi phục bằng `git checkout` trên file chưa được theo dõi khiến đột biến ở lại; bắt được nhờ `grep` lại trước khi commit ([REPO AI_WORKLOG.md:129-131]).


## [15](15-ai-assisted-dev-workflow.md) — 15 · Quy trình phát triển có AI hỗ trợ: executor/verifier, prompt tác vụ, sổ theo dõi, worktree, merge/tag, sự cố và bí mật

1. **"Bạn dùng AI khi phát triển thế nào mà vẫn kiểm soát chất lượng?"** — Tách executor/verifier, verifier tái tạo mọi số và đọc test để tìm test không thể fail, nhật ký trung thực có mục "AI làm sai gì", và quyết định mở luôn hỏi chủ dự án ([REPO agents/prompts/99-VERIFY.md:12-19]).
2. **"AI làm sai điều gì trong dự án của bạn?"** — Bịa xác nhận của chủ dự án (subagent), khẳng định nhánh dựa trên `dev` mà không kiểm, số đếm cũ, thông điệp commit sai về mức rủi ro — mỗi cái có cách bắt và sửa ([REPO AI_WORKLOG.md:601-604], [REPO AI_WORKLOG.md:760-768]).
3. **"Bạn quản lý nhánh và phát hành ra sao?"** — Nhánh tác vụ từ `dev`, merge về `dev`; `main` chỉ khi chủ dự án nói; tag `eval-freeze-v1` và `v1.0-submission` ([REPO CLAUDE.md:15]).
4. **"Làm việc song song nhiều phiên thế nào?"** — Git worktree riêng cho từng phiên; lưu ý dữ liệu bị ignore và editable install ([REPO src/knowledge_assistant/config.py:18-30]).
5. **"Bạn bảo vệ bí mật thế nào?"** — Chỉ đọc từ môi trường, che khi ghi, không in, quét lịch sử git (198 commit, 0 lần) ([REPO docs/plans/task-ledger.md:38-38]).
6. **"Bạn quyết định điều gì và AI quyết định điều gì?"** — AI thực thi và đề xuất; các điểm quyết định (ngưỡng, phương pháp chấm, luật hit) do chủ dự án, ghi ngày vào spec/ADR ([REPO docs/specs/evaluation-spec.md:3-3]).


## [16](16-beyond-this-project.md) — 16 · Vượt ra ngoài dự án: lộ trình các chủ đề cấp cao hơn

1. **"Bạn sẽ cải thiện hệ RAG này thế nào?"** — Theo bằng chứng: mở rộng eval, ngưỡng theo arm, judge thứ hai, chạy đường lỗi thật; sau đó hybrid + đa dạng hoá biến thể cho ca gần trùng ([REPO docs/reports/epics/EPIC-06-experiment.md:586-603]).
2. **"Khi nào dùng hybrid search?"** — Khi có nhiều định danh/từ khoá chính xác (tên API) mà embedding làm mờ; kết hợp BM25 và dense bằng RRF; phải đo lại ([REPO agents/prompts/13-BONUS-001-hybrid-and-query-rewrite.md:7-7]).
3. **"Reranking có đáng không?"** — Tuỳ bằng chứng: nếu chunk đúng ở top-5 nhưng xếp thấp và gây lỗi thì có; ở EXP-001 tầng `ranking` không kích hoạt nên chưa có lý do rõ ([REPO docs/reports/epics/EPIC-06-experiment.md:466-466]).
4. **"Rủi ro khi cho người dùng upload tài liệu?"** — Prompt injection, riêng tư, thiếu ground truth, citation theo trang; README liệt kê ([REPO README.md:312-327]).
5. **"Bạn đo tác động của một thay đổi như thế nào?"** — Bộ eval đóng băng, một biến đổi, kiểm định ghép cặp + CI, đọc ca bất đồng (file 10–13).
6. **"Bạn dự phòng gì cho lỗi API thật chưa gặp?"** — Repo có retry/fallback nhưng chưa từng thấy 429/503 thật; việc tiếp theo là kiểm chứng đường đó ([REPO AI_WORKLOG.md:883-902]).
