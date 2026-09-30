# Glossary — thuật ngữ · giải thích tiếng Việt · file chủ (home file)
> Commit: 762b754 (tag `v1.0-submission`) · Mỗi dòng: thuật ngữ tiếng Anh (giữ nguyên) · giải thích ngắn bằng tiếng Việt · liên kết tới nơi thuật ngữ được **dạy đầy đủ** (số file + số mục). Liên kết được sinh bằng `_tools/expand_links.py` và **fail nếu mục không tồn tại**. Giải thích ở đây là bản rút gọn; ví dụ và `[REPO path:line]` nằm ở file chủ. Thuật ngữ nào chỉ là kiến thức phổ thông (`[GENERAL]`) được ghi rõ ở file chủ.

## A. Python và công cụ
| Term | Giải thích | Home |
|---|---|---|
| `import` / module / package | Cách Python nạp code từ file/thư mục khác; package là thư mục có `__init__.py` | [01 §1.1](01-python-for-csharp-devs.md) |
| type hint | Chú thích kiểu (`str`, `list[int]`, `X \| None`) — **không** bị ép lúc chạy | [01 §1.2](01-python-for-csharp-devs.md) |
| `@dataclass(frozen=True)` | Class dữ liệu bất biến, gần `record` của C# | [01 §1.3](01-python-for-csharp-devs.md) |
| f-string | Chuỗi nội suy `f"{x}"`; `!r` in bản `repr` | [01 §1.4](01-python-for-csharp-devs.md) |
| list / dict / tuple / set | Bốn kiểu tập hợp; `dict` giữ thứ tự chèn | [01 §1.5](01-python-for-csharp-devs.md) |
| comprehension | Biểu thức tạo list/dict/set gọn: `[x for x in xs if ...]` | [01 §1.6](01-python-for-csharp-devs.md) |
| `try/except`, `raise ... from` | Xử lý lỗi; `from` giữ nguyên lỗi gốc (như `InnerException`) | [01 §1.7](01-python-for-csharp-devs.md) |
| `pathlib.Path` | Đường dẫn dạng object; `/` để ghép | [01 §1.8](01-python-for-csharp-devs.md) |
| class, `__init__`, `self`, `_private` | Định nghĩa class; `_` là quy ước "nội bộ" | [01 §2.1](01-python-for-csharp-devs.md) |
| `Protocol` | Interface kiểu structural: khớp theo hình dạng, không cần kế thừa | [01 §2.2](01-python-for-csharp-devs.md) |
| dependency as function | Truyền hàm (`clock`, `sleep`, `jitter`) làm phụ thuộc để test xác định | [01 §2.3](01-python-for-csharp-devs.md) |
| keyword-only argument, `*args`, `**kwargs` | Tham số bắt buộc gọi theo tên; gom tham số thừa | [01 §2.4](01-python-for-csharp-devs.md) |
| context manager (`with`) | Đối tượng có `__enter__/__exit__`; tương đương `using` | [01 §2.5](01-python-for-csharp-devs.md) |
| `Enum` trộn `str` | Hằng có tên, so sánh được với chuỗi | [01 §2.6](01-python-for-csharp-devs.md) |
| `lambda`, `dict.fromkeys` | Hàm nhỏ; `dict.fromkeys` khử trùng lặp **giữ thứ tự** | [01 §2.8](01-python-for-csharp-devs.md) |
| regex, lookahead/lookbehind | Biểu thức chính quy; kiểm điều kiện xung quanh mà không tiêu thụ ký tự | [01 §3.1](01-python-for-csharp-devs.md) |
| `struct`, `bytes` | Đóng gói/giải nén dữ liệu nhị phân (vector float32) | [01 §3.2](01-python-for-csharp-devs.md) |
| `Fraction`, `math.comb` | Số hữu tỉ chính xác; tổ hợp — tránh sai số float | [01 §3.3](01-python-for-csharp-devs.md) |
| `__post_init__` | Kiểm tra bất biến ngay sau khi dựng dataclass | [01 §3.4](01-python-for-csharp-devs.md) |
| `getattr(obj, name, default)` | Đọc thuộc tính với giá trị mặc định (dùng cho object của SDK) | [01 §3.5](01-python-for-csharp-devs.md) |
| `from __future__ import annotations` | Hoãn đánh giá chú thích kiểu (tham chiếu tới class chưa định nghĩa) | [01 §3.6](01-python-for-csharp-devs.md) |
| reading recipe / decoder table | Quy trình 6 bước + bảng ký hiệu để **đọc** code Python lạ | [01b §1.1](01b-python-code-reading-guide.md) |
| virtual environment (`.venv`) | Bản sao Python + thư viện riêng cho từng dự án | [02 §1.1](02-python-tooling-and-dependencies.md) |
| `requirements.txt` | Danh sách phụ thuộc "phẳng" với ràng buộc phiên bản | [02 §1.2](02-python-tooling-and-dependencies.md) |
| `pyproject.toml` | Metadata dự án + phụ thuộc + cấu hình công cụ (như `.csproj`) | [02 §1.3](02-python-tooling-and-dependencies.md) |
| extras, editable install (`-e`) | Nhóm phụ thuộc tuỳ chọn; cài liên kết tới thư mục nguồn | [02 §2.1](02-python-tooling-and-dependencies.md) |
| src layout, `sys.path`, `PYTHONPATH` | Cách Python tìm module; mã nằm trong `src/` | [02 §2.2](02-python-tooling-and-dependencies.md) |
| `python -m` | Chạy module theo tên (bắt buộc với import tương đối) | [02 §2.3](02-python-tooling-and-dependencies.md) |
| environment variable, `.env`, `python-dotenv` | Cấu hình/bí mật ngoài code; `load_dotenv` mặc định **không ghi đè** biến đã có | [02 §2.4](02-python-tooling-and-dependencies.md) |
| `PROJECT_ROOT` | Neo đường dẫn vào gốc repo, không phụ thuộc thư mục làm việc | [02 §2.5](02-python-tooling-and-dependencies.md) |
| pytest config, marker `gemini` | `addopts = "-m 'not gemini'"` loại test cần API thật | [02 §3.1](02-python-tooling-and-dependencies.md) |
| `OPENBLAS_NUM_THREADS` | Giới hạn luồng của thư viện đại số tuyến tính trên máy ít RAM | [02 §3.2](02-python-tooling-and-dependencies.md) |

## B. Kiến trúc và GUI
| Term | Giải thích | Home |
|---|---|---|
| layered/clean architecture, dependency rule | presentation → application → core ← infrastructure; core không import thư viện ngoài | [03 §1.1](03-architecture-and-gui.md) |
| ADR (Architecture Decision Record) | Bản ghi một quyết định kiến trúc và lý do | [03 §1.3](03-architecture-and-gui.md) |
| port / adapter | Port = `Protocol` trong core; adapter = cài đặt trong infrastructure | [03 §2.1](03-architecture-and-gui.md) |
| Decorator pattern (`CachingEmbedder`) | Bọc một `Embedder` để thêm cache mà không đổi interface | [03 §2.2](03-architecture-and-gui.md) |
| composition root | Nơi duy nhất "lắp" các mảnh với nhau (`composition.py`) | [03 §2.3](03-architecture-and-gui.md) |
| error boundary | Lỗi của nhà cung cấp không rời infrastructure; core chỉ thấy lỗi của mình | [03 §2.4](03-architecture-and-gui.md) |
| architecture test | Test dùng `ast` kiểm luật import giữa các tầng | [03 §2.5](03-architecture-and-gui.md) |
| domain model | Đối tượng nghiệp vụ độc lập định dạng (`Document`, `Citation`…) | [03 §2.6](03-architecture-and-gui.md) |
| MVVM | View ↔ ViewModel ↔ Port; GUI không chứa logic nghiệp vụ | [03 §3.1](03-architecture-and-gui.md) |
| `QThreadPool` / `QRunnable` / `Signal` | Chạy việc nặng ngoài luồng GUI, trả kết quả về luồng GUI | [03 §3.2](03-architecture-and-gui.md) |
| thread affinity, `Lock`, lazy service | SQLite gắn với luồng tạo ra; tạo service lười dưới `Lock` | [03 §3.3](03-architecture-and-gui.md) |
| lazy import, `--fake` | Import khi cần; chế độ demo offline không cần key | [03 §3.5](03-architecture-and-gui.md) |

## C. Pipeline RAG, embedding, chunking, truy xuất
| Term | Giải thích | Home |
|---|---|---|
| RAG (Retrieval-Augmented Generation) | Tìm đoạn liên quan trong kho rồi cho LLM trả lời dựa trên chúng | [05 §1.1](05-rag-fundamentals.md) |
| offline vs online phase | Xây index (một lần) vs trả lời (mỗi câu hỏi) | [05 §1.2](05-rag-fundamentals.md) |
| corpus | Bộ tài liệu cố định (24 tài liệu chấp nhận) | [05 §1.3](05-rag-fundamentals.md) |
| grounded answer, "insufficient" | Trả lời dựa trên ngữ cảnh; nếu không đủ phải nói rõ | [05 §1.5](05-rag-fundamentals.md) |
| `AnswerResult` | Hợp đồng đầu ra của use case (câu trả lời, citation, độ trễ…) | [05 §2.5](05-rag-fundamentals.md) |
| language detection (vi/en) | Đoán ngôn ngữ câu hỏi từ ký tự tiếng Việt đặc trưng | [05 §2.4](05-rag-fundamentals.md) |
| cross-lingual retrieval | Câu hỏi tiếng Việt, tài liệu tiếng Anh | [05 §3.2](05-rag-fundamentals.md) |
| embedding | Vector số biểu diễn "nghĩa" của một đoạn văn | [06 §1.1](06-embeddings-and-vector-search.md) |
| dimension (768), `model_id` | Số chiều vector; khoá định danh model+kích thước | [06 §1.2](06-embeddings-and-vector-search.md) |
| normalization, dot product, cosine | Chuẩn hoá vector; tích vô hướng = cosine khi chuẩn; `score = 1 − distance` | [06 §1.3](06-embeddings-and-vector-search.md) |
| vector database (ChromaDB) | Kho lưu vector + tìm kiếm gần đúng; chạy nhúng trong tiến trình | [06 §1.4](06-embeddings-and-vector-search.md) |
| batching, `plan_calls` | Chia text thành các lô (≤ 45 text, nửa ngân sách token/phút) | [06 §2.2](06-embeddings-and-vector-search.md) |
| token estimate (`chars/4`) | Ước lượng token để lập kế hoạch quota | [06 §2.3](06-embeddings-and-vector-search.md) |
| embedding cache | Bảng SQLite khoá bằng hash; chỉ gửi phần chưa có | [06 §2.5](06-embeddings-and-vector-search.md) |
| `ChromaVectorStore` | Adapter Chroma: upsert, tìm, kiểm cấu hình khi mở | [06 §2.6](06-embeddings-and-vector-search.md) |
| HNSW, approximate nearest neighbour | Cấu trúc đồ thị cho tìm gần đúng — nhanh nhưng không xác định tuyệt đối | [06 §3.1](06-embeddings-and-vector-search.md) |
| quota plan | Tính tổng request theo ngày (709 + 859 trên hai ngày) | [06 §3.2](06-embeddings-and-vector-search.md) |
| chunk / chunking | Đoạn văn bản được cắt để nhúng và truy xuất | [07 §1.1](07-chunking-and-retrieval.md) |
| fixed-size chunker (Arm B) | Cửa sổ cố định 1600 ký tự, overlap 200 | [07 §1.2](07-chunking-and-retrieval.md) |
| header-aware chunker (Arm A) | Cắt theo H2/H3, giữ code/bảng nguyên khối | [07 §2.1](07-chunking-and-retrieval.md) |
| overlap, atomic block | Phần chồng lấn giữa chunk; khối code/bảng không bị cắt | [07 §2.2](07-chunking-and-retrieval.md) |
| `display_text` / `embed_text` | Văn bản hiển thị vs văn bản đem đi nhúng (có heading path, bỏ link) | [07 §1.3](07-chunking-and-retrieval.md) |
| `chunk_id`, determinism | `source:config:index:04d` — xác định nên index chạy lại là no-op | [07 §2.6](07-chunking-and-retrieval.md) |
| top-k, over-fetch, dedup (`passage_hash`) | Lấy dư (5+10) rồi khử trùng theo đoạn, giữ 5 | [07 §3.1](07-chunking-and-retrieval.md) |
| refusal gate, threshold 0.686 | Top-1 < ngưỡng → không gọi LLM; ngưỡng = 0.7360 − 0.05 | [07 §3.3](07-chunking-and-retrieval.md) |
| tie-break by `chunk_id` | Phá hoà xác định khi hai chunk cùng điểm | [07 §3.5](07-chunking-and-retrieval.md) |
| index idempotency | Chỉ nhúng chunk chưa có trong store | [05 §2.3](05-rag-fundamentals.md) |

## D. Sinh câu trả lời và gọi LLM API
| Term | Giải thích | Home |
|---|---|---|
| prompt template, version | Prompt là file có phiên bản (`answer_v2`), không nằm trong code | [08 §1.1](08-generation-and-prompting.md) |
| structured output / JSON mode, schema | Ép model trả JSON đúng khoá; schema là JSON Schema | [08 §1.3](08-generation-and-prompting.md) |
| "insufficient" refusal rule | Model đặt `insufficient=true`; câu trả lời hiển thị là thông báo cố định | [08 §1.4](08-generation-and-prompting.md) |
| `parse_answer_json` | Kiểm kiểu chặt đầu ra của model; sai → `GenerationError` | [08 §1.5](08-generation-and-prompting.md) |
| one-pass placeholder rendering | Một lượt `re.sub`; `{}` trong dữ liệu không bị coi là placeholder | [08 §2.1](08-generation-and-prompting.md) |
| passage numbering `[n]` | Đánh số passage 1..k; là khoá liên kết prompt ↔ citation | [08 §2.2](08-generation-and-prompting.md) |
| citation marker, `resolve_citations` | Đọc `[n]` ngoài code; số ngoài 1..k bị bỏ và ghi lại | [08 §2.4](08-generation-and-prompting.md) |
| excerpt | 300 ký tự đầu của passage, cắt ở ranh giới từ, không thêm "…" | [08 §2.5](08-generation-and-prompting.md) |
| uncited sentences | Chỉ số chẩn đoán: câu ≥ 5 từ không có marker | [08 §2.6](08-generation-and-prompting.md) |
| prompt injection | Văn bản trong dữ liệu chứa lệnh nhắm vào model — repo chưa phòng thủ (corpus cố định) | [08 §3.3](08-generation-and-prompting.md) |
| temperature 0 | Giảm phương sai đầu ra; không đảm bảo giống hệt | [08 §3.2](08-generation-and-prompting.md) |
| rate limit (RPM/TPM/RPD) | Giới hạn request/phút, token/phút, request/ngày theo project & model | [09 §1.1](09-llm-api-engineering.md) |
| model pinning | Tên model chỉ trong cấu hình, không `-latest` | [09 §1.2](09-llm-api-engineering.md) |
| token, thinking token | Đơn vị tính phí/giới hạn; token "suy nghĩ" tính như output | [09 §1.3](09-llm-api-engineering.md) |
| failure kinds (`quota`/`unavailable`/`other`) | Ba loại lỗi API dùng chung cho retry, log, GUI | [09 §1.4](09-llm-api-engineering.md) |
| sliding-window throttle | Giữ lịch sử 60s; chờ nếu không còn chỗ | [09 §2.1](09-llm-api-engineering.md) |
| retry, exponential backoff, jitter, `Retry-After` | Thử lại với chờ tăng dần + ngẫu nhiên; tôn trọng gợi ý của server; trần 120s | [09 §2.2](09-llm-api-engineering.md) |
| `classify_failure` | Hàm duy nhất biết lỗi nào của SDK là lỗi nhà cung cấp | [09 §2.3](09-llm-api-engineering.md) |
| fallback model | Model dự phòng, đúng một lần, ngân sách output riêng | [09 §2.4](09-llm-api-engineering.md) |
| `finish_reason` check | `MAX_TOKENS`/rỗng → `GenerationError`, không retry, không fallback | [09 §2.6](09-llm-api-engineering.md) |
| key redaction | Che API key ở mọi đường ghi ra | [09 §3.1](09-llm-api-engineering.md) |
| daily quota reset (timezone) | Reset nửa đêm giờ Pacific = 14:00 UTC+7 (PDT) / 15:00 UTC+7 (PST); chủ dự án xác nhận, phần tài liệu Google là `[GENERAL]` | [09 §3.2](09-llm-api-engineering.md) |
| cost estimate with `null` prices | Ước tính chi phí, không bao giờ đoán giá thiếu | [09 §3.4](09-llm-api-engineering.md) |

## E. Đánh giá, judge, thống kê, thí nghiệm
| Term | Giải thích | Home |
|---|---|---|
| ground truth | Đáp án chuẩn + nguồn kỳ vọng, viết **trước** khi có index | [10 §1.2](10-evaluation-design.md) |
| dev set vs eval set | Bộ chỉnh (6 case) vs bộ báo cáo (36 case) — không được chỉnh trên eval | [10 §1.3](10-evaluation-design.md) |
| result labels (OD-5) | `correct`, `partially_correct`, `incorrect`, `false_refusal`, `correct_refusal`, `hallucination` | [10 §1.4](10-evaluation-design.md) |
| hit@k, MRR | Có trúng trong top-k không; trung bình `1/hạng` | [10 §1.5](10-evaluation-design.md) |
| section hit, span overlap | Trúng theo offset ký tự nửa mở, không so tên heading | [10 §2.1](10-evaluation-design.md) |
| evidence slot | Nhóm nguồn tương đương; case trúng khi mọi slot có một nguồn | [10 §2.2](10-evaluation-design.md) |
| lenient vs strict | Có/không tính nguồn thay thế; headline lenient, luôn báo kèm strict | [10 §2.3](10-evaluation-design.md) |
| duplicate rule | Section-level tính bản trùng bị loại; source-level thì không | [10 §2.4](10-evaluation-design.md) |
| evidence hit | Mọi required point có quote nguyên văn trong chunk top-k | [10 §2.5](10-evaluation-design.md) |
| `map_result` | Bảng ánh xạ xác định từ dữ liệu judge sang nhãn | [10 §2.6](10-evaluation-design.md) |
| points-covered | `(yes + 0.5·partial)/số point required` | [10 §2.7](10-evaluation-design.md) |
| denominators (answerable / unanswerable / answered) | Ba mẫu số không được lẫn; record lỗi bị loại và liệt kê | [10 §2.8](10-evaluation-design.md) |
| freeze (tag + hash + amendment) | Đóng băng bộ câu hỏi; sửa im lặng bị phát hiện | [10 §3.1](10-evaluation-design.md) |
| threats to validity | Các mối đe doạ tính hợp lệ (ngưỡng chỉnh trên A, judge = model, n nhỏ…) | [10 §3.2](10-evaluation-design.md) |
| bias controls, parallel EN/VI group | Kiểm soát thiên lệch; nhóm song song tách hiệu ứng ngôn ngữ | [10 §3.3](10-evaluation-design.md) |
| LLM-as-judge | Dùng LLM chấm đầu ra theo rubric; không phải chân lý | [11 §1.1](11-llm-as-judge.md) |
| answer check / refusal check | Hai kiểu chấm: coverage từng point vs "trình bày nội dung liên quan như đáp án" | [11 §1.2](11-llm-as-judge.md) |
| strict verdict parse, `judge_error` | Sai một chút là `judge_error`, không đoán | [11 §2.2](11-llm-as-judge.md) |
| judgement cache & validity | Khoá `(case, arm, sha256(answer), version)`; hash prompt/model khác → từ chối | [11 §2.3](11-llm-as-judge.md) |
| self-preference bias | Judge có xu hướng ưu ái văn bản giống của chính nó | [11 §3.1](11-llm-as-judge.md) |
| spot-check, Cohen's κ | Người kiểm mù mẫu nhỏ; κ = đồng thuận đã trừ phần ngẫu nhiên (0.688) | [11 §3.2](11-llm-as-judge.md) |
| paired design | Cùng câu hỏi trên cả hai arm; so mỗi câu với chính nó | [12 §1.2](12-statistics-for-experiments.md) |
| p-value, confidence interval (CI) | Xác suất dữ liệu cực đoan nếu không có khác biệt; khoảng giá trị Δ chấp nhận được | [12 §1.3](12-statistics-for-experiments.md) |
| nearest-rank percentile | Phân vị ở hạng `ceil(p/100·n)`, không nội suy | [12 §1.4](12-statistics-for-experiments.md) |
| McNemar exact | Kiểm định ghép cặp cho kết quả 0/1 dựa trên các cặp bất đồng | [12 §2.1](12-statistics-for-experiments.md) |
| Wilcoxon signed-rank exact | Kiểm định ghép cặp cho giá trị liên tục (độ trễ, token) | [12 §2.3](12-statistics-for-experiments.md) |
| paired bootstrap | Lấy mẫu có hoàn lại **chỉ số cặp**, 10 000 lần, seed 42 → CI | [12 §2.4](12-statistics-for-experiments.md) |
| wording rule | `p ≥ 0.05` → "no statistically reliable difference at n = X", không nêu người thắng | [12 §2.5](12-statistics-for-experiments.md) |
| statistical power | Cần ≥ 6 cặp bất đồng một phía để p < 0.05; n nhỏ → khó đạt ý nghĩa | [12 §2.2](12-statistics-for-experiments.md) |
| multiple comparisons | Chạy nhiều phép thử → dương tính giả; repo không hiệu chỉnh | [12 §3.1](12-statistics-for-experiments.md) |
| confounder | Yếu tố gây nhiễu không phải chunker (thứ tự chạy, cache) | [12 §3.3](12-statistics-for-experiments.md) |
| controlled experiment, held-constant | Chỉ đổi chunker; mọi thứ khác giữ hằng và được máy kiểm | [13 §1.1](13-case-study-exp-001.md) |
| failure analysis (stages) | Phân loại lỗi theo tầng bằng cây quy tắc có thứ tự | [13 §2.4](13-case-study-exp-001.md) |
| discordant case | Case hai arm cho kết quả khác nhau — đọc ở mức chunk | [13 §2.3](13-case-study-exp-001.md) |
| measurement-side error | Lỗi do cách đo (judge, ngưỡng), không phải lỗi hệ thống | [13 §3.1](13-case-study-exp-001.md) |
| honest conclusion | Nói đúng mức dữ liệu cho phép, nêu cả điều **không** kết luận | [13 §3.2](13-case-study-exp-001.md) |

## F. Dữ liệu, độ bền, kiểm thử, quy trình
| Term | Giải thích | Home |
|---|---|---|
| JSONL (JSON Lines) | Mỗi dòng một JSON; thêm bản ghi = nối dòng | [04 §1.1](04-data-io-and-reliability-patterns.md) |
| SHA-256 / content hash | Danh tính nội dung; cùng nội dung → cùng hash | [04 §1.2](04-data-io-and-reliability-patterns.md) |
| idempotent / deterministic / append-only | Chạy nhiều lần như một; cùng vào cùng ra; chỉ thêm | [04 §1.3](04-data-io-and-reliability-patterns.md) |
| `fsync`, torn write | Ghi xuống đĩa thật; dòng cụt do crash được nhận diện và cắt | [04 §2.1](04-data-io-and-reliability-patterns.md) |
| "last line wins" (`latest_records`) | Trạng thái hiện tại = bản ghi cuối theo khoá | [04 §2.2](04-data-io-and-reliability-patterns.md) |
| atomic replace (`os.replace`) | Ghi tmp rồi đổi tên — người đọc thấy bản cũ hoặc mới | [04 §2.3](04-data-io-and-reliability-patterns.md) |
| cache key, float32 BLOB | Khoá = hash(model\|task\|text); vector lưu 4 byte/số | [04 §2.4](04-data-io-and-reliability-patterns.md) |
| commit per provider call | Một transaction mỗi lời gọi trả tiền — không mất kết quả đã trả | [04 §2.5](04-data-io-and-reliability-patterns.md) |
| resume + manifest check | Từ chối tiếp tục khi thiết lập đổi (`RunConfigMismatch`) | [04 §3.1](04-data-io-and-reliability-patterns.md) |
| UTF-8 + LF | Ép LF (`.gitattributes`) để hash/diff ổn định | [04 §3.3](04-data-io-and-reliability-patterns.md) |
| pytest, fixture, `tmp_path` | Test bằng `assert` trần; fixture tiêm bằng tên tham số | [14 §1.1](14-testing-and-quality.md) |
| fake vs stub vs mock | Fake = cài đặt đơn giản thật; mock kiểm tương tác | [14 §1.3](14-testing-and-quality.md) |
| `FakeClock`, `FakeEmbedder`, `api_error` | Bộ fake có kịch bản của repo | [14 §2.1](14-testing-and-quality.md) |
| `parametrize` | Một hàm test, nhiều bộ dữ liệu | [14 §2.4](14-testing-and-quality.md) |
| flaky test | Test đôi khi fail; repo ghi nhận (15/15 pass) thay vì che | [14 §3.1](14-testing-and-quality.md) |
| mutation testing | Cố tình phá code để chứng minh test bắt được lỗi; đột biến "sống sót" | [14 §3.2](14-testing-and-quality.md) |
| executor / verifier | Hai vai: người làm và người kiểm độc lập (`99-VERIFY`) | [15 §1.1](15-ai-assisted-dev-workflow.md) |
| task ledger, status `verified` | Sổ trạng thái tác vụ; `verified with fixes` chưa đủ để đi tiếp | [15 §1.3](15-ai-assisted-dev-workflow.md) |
| "Explain it back" | 3–5 ý chủ dự án phải bảo vệ được khi phỏng vấn | [15 §1.2](15-ai-assisted-dev-workflow.md) |
| `dev` / `main` / tag | `dev` tích hợp; `main` ổn định, chỉ merge khi chủ dự án nói; tag đóng băng/nộp | [15 §2.3](15-ai-assisted-dev-workflow.md) |
| git worktree | Thư mục làm việc thứ hai cho cùng repo, dùng cho phiên song song | [15 §2.4](15-ai-assisted-dev-workflow.md) |
| workflow incidents | Các sự cố quy trình thật (subagent bịa xác nhận…) | [15 §3.1](15-ai-assisted-dev-workflow.md) |
| secret scan | Quét lịch sử git tìm khoá; redaction; `.env` git-ignored | [15 §3.3](15-ai-assisted-dev-workflow.md) |
| GitNexus impact analysis | Phân tích tác động trước khi sửa symbol | [15 §3.2](15-ai-assisted-dev-workflow.md) |
| BM25, RRF (hybrid search) | Tìm theo từ khoá + hợp nhất thứ hạng; **chưa** xây trong repo | [16 §2.1](16-beyond-this-project.md) |
| reranking | Cross-encoder xếp hạng lại ứng viên; thêm khi có bằng chứng cần | [16 §2.2](16-beyond-this-project.md) |
| parent–child / semantic chunking | Kỹ thuật chunking nâng cao; nhắm vào lỗi "một chunk có đủ đáp án không" | [16 §2.3](16-beyond-this-project.md) |
| query rewriting, HyDE | Viết lại/sinh truy vấn giả trước khi tìm | [16 §2.4](16-beyond-this-project.md) |
| MMR, metadata filter | Đa dạng hoá kết quả; lọc theo metadata | [16 §2.5](16-beyond-this-project.md) |
