# Glossary — thuật ngữ · giải thích tiếng Việt · file chủ (home file)
> Commit: 762b754 (tag `v1.0-submission`) · Mỗi dòng: thuật ngữ tiếng Anh (giữ nguyên) · giải thích ngắn bằng tiếng Việt · liên kết tới nơi thuật ngữ được **dạy đầy đủ** (số file + số mục). Liên kết được sinh bằng `_tools/expand_links.py` và **fail nếu mục không tồn tại**. Giải thích ở đây là bản rút gọn; ví dụ và `[REPO path:line]` nằm ở file chủ. Thuật ngữ nào chỉ là kiến thức phổ thông (`[GENERAL]`) được ghi rõ ở file chủ.

## A. Python và công cụ
| Term | Giải thích | Home |
|---|---|---|
| `import` / module / package | Cách Python nạp code từ file/thư mục khác; package là thư mục có `__init__.py` | @@LINK 01|Module, package@@ |
| type hint | Chú thích kiểu (`str`, `list[int]`, `X \| None`) — **không** bị ép lúc chạy | @@LINK 01|Type hint@@ |
| `@dataclass(frozen=True)` | Class dữ liệu bất biến, gần `record` của C# | @@LINK 01|dataclass@@ |
| f-string | Chuỗi nội suy `f"{x}"`; `!r` in bản `repr` | @@LINK 01|Hàm, tham số mặc định@@ |
| list / dict / tuple / set | Bốn kiểu tập hợp; `dict` giữ thứ tự chèn | @@LINK 01|Bốn kiểu tập hợp@@ |
| comprehension | Biểu thức tạo list/dict/set gọn: `[x for x in xs if ...]` | @@LINK 01|Comprehension@@ |
| `try/except`, `raise ... from` | Xử lý lỗi; `from` giữ nguyên lỗi gốc (như `InnerException`) | @@LINK 01|Exception: `try/except`@@ |
| `pathlib.Path` | Đường dẫn dạng object; `/` để ghép | @@LINK 01|pathlib@@ |
| class, `__init__`, `self`, `_private` | Định nghĩa class; `_` là quy ước "nội bộ" | @@LINK 01|Class, `__init__`@@ |
| `Protocol` | Interface kiểu structural: khớp theo hình dạng, không cần kế thừa | @@LINK 01|Protocol@@ |
| dependency as function | Truyền hàm (`clock`, `sleep`, `jitter`) làm phụ thuộc để test xác định | @@LINK 01|Truyền hàm làm dependency@@ |
| keyword-only argument, `*args`, `**kwargs` | Tham số bắt buộc gọi theo tên; gom tham số thừa | @@LINK 01|Keyword-only@@ |
| context manager (`with`) | Đối tượng có `__enter__/__exit__`; tương đương `using` | @@LINK 01|Context manager@@ |
| `Enum` trộn `str` | Hằng có tên, so sánh được với chuỗi | @@LINK 01|`Enum` trộn@@ |
| `lambda`, `dict.fromkeys` | Hàm nhỏ; `dict.fromkeys` khử trùng lặp **giữ thứ tự** | @@LINK 01|`lambda`@@ |
| regex, lookahead/lookbehind | Biểu thức chính quy; kiểm điều kiện xung quanh mà không tiêu thụ ký tự | @@LINK 01|Regex như một mini-parser@@ |
| `struct`, `bytes` | Đóng gói/giải nén dữ liệu nhị phân (vector float32) | @@LINK 01|Dữ liệu nhị phân@@ |
| `Fraction`, `math.comb` | Số hữu tỉ chính xác; tổ hợp — tránh sai số float | @@LINK 01|`fractions.Fraction`@@ |
| `__post_init__` | Kiểm tra bất biến ngay sau khi dựng dataclass | @@LINK 01|`__post_init__`@@ |
| `getattr(obj, name, default)` | Đọc thuộc tính với giá trị mặc định (dùng cho object của SDK) | @@LINK 01|`getattr`@@ |
| `from __future__ import annotations` | Hoãn đánh giá chú thích kiểu (tham chiếu tới class chưa định nghĩa) | @@LINK 01|from __future__ import annotations@@ |
| reading recipe / decoder table | Quy trình 6 bước + bảng ký hiệu để **đọc** code Python lạ | @@LINK 01b|Quy trình đọc một file@@ |
| virtual environment (`.venv`) | Bản sao Python + thư viện riêng cho từng dự án | @@LINK 02|Virtual environment@@ |
| `requirements.txt` | Danh sách phụ thuộc "phẳng" với ràng buộc phiên bản | @@LINK 02|`pip` và `requirements.txt`@@ |
| `pyproject.toml` | Metadata dự án + phụ thuộc + cấu hình công cụ (như `.csproj`) | @@LINK 02|`pyproject.toml`: metadata@@ |
| extras, editable install (`-e`) | Nhóm phụ thuộc tuỳ chọn; cài liên kết tới thư mục nguồn | @@LINK 02|Extras tuỳ chọn@@ |
| src layout, `sys.path`, `PYTHONPATH` | Cách Python tìm module; mã nằm trong `src/` | @@LINK 02|**src layout**@@ |
| `python -m` | Chạy module theo tên (bắt buộc với import tương đối) | @@LINK 02|Chạy code@@ |
| environment variable, `.env`, `python-dotenv` | Cấu hình/bí mật ngoài code; `load_dotenv` mặc định **không ghi đè** biến đã có | @@LINK 02|Biến môi trường@@ |
| `PROJECT_ROOT` | Neo đường dẫn vào gốc repo, không phụ thuộc thư mục làm việc | @@LINK 02|Đường dẫn theo gốc repo@@ |
| pytest config, marker `gemini` | `addopts = "-m 'not gemini'"` loại test cần API thật | @@LINK 02|Cấu hình pytest@@ |
| `OPENBLAS_NUM_THREADS` | Giới hạn luồng của thư viện đại số tuyến tính trên máy ít RAM | @@LINK 02|`OPENBLAS_NUM_THREADS=1`@@ |

## B. Kiến trúc và GUI
| Term | Giải thích | Home |
|---|---|---|
| layered/clean architecture, dependency rule | presentation → application → core ← infrastructure; core không import thư viện ngoài | @@LINK 03|Bốn lớp@@ |
| ADR (Architecture Decision Record) | Bản ghi một quyết định kiến trúc và lý do | @@LINK 03|ADR@@ |
| port / adapter | Port = `Protocol` trong core; adapter = cài đặt trong infrastructure | @@LINK 03|Ports & adapters@@ |
| Decorator pattern (`CachingEmbedder`) | Bọc một `Embedder` để thêm cache mà không đổi interface | @@LINK 03|Decorator pattern@@ |
| composition root | Nơi duy nhất "lắp" các mảnh với nhau (`composition.py`) | @@LINK 03|Composition root@@ |
| error boundary | Lỗi của nhà cung cấp không rời infrastructure; core chỉ thấy lỗi của mình | @@LINK 03|Error boundary@@ |
| architecture test | Test dùng `ast` kiểm luật import giữa các tầng | @@LINK 03|Architecture test@@ |
| domain model | Đối tượng nghiệp vụ độc lập định dạng (`Document`, `Citation`…) | @@LINK 03|Domain model@@ |
| MVVM | View ↔ ViewModel ↔ Port; GUI không chứa logic nghiệp vụ | @@LINK 03|MVVM@@ |
| `QThreadPool` / `QRunnable` / `Signal` | Chạy việc nặng ngoài luồng GUI, trả kết quả về luồng GUI | @@LINK 03|Chạy việc nặng@@ |
| thread affinity, `Lock`, lazy service | SQLite gắn với luồng tạo ra; tạo service lười dưới `Lock` | @@LINK 03|Thread affinity@@ |
| lazy import, `--fake` | Import khi cần; chế độ demo offline không cần key | @@LINK 03|Import lười@@ |

## C. Pipeline RAG, embedding, chunking, truy xuất
| Term | Giải thích | Home |
|---|---|---|
| RAG (Retrieval-Augmented Generation) | Tìm đoạn liên quan trong kho rồi cho LLM trả lời dựa trên chúng | @@LINK 05|RAG là gì@@ |
| offline vs online phase | Xây index (một lần) vs trả lời (mỗi câu hỏi) | @@LINK 05|Hai pha@@ |
| corpus | Bộ tài liệu cố định (24 tài liệu chấp nhận) | @@LINK 05|Corpus@@ |
| grounded answer, "insufficient" | Trả lời dựa trên ngữ cảnh; nếu không đủ phải nói rõ | @@LINK 05|Hai "lớp từ chối"@@ |
| `AnswerResult` | Hợp đồng đầu ra của use case (câu trả lời, citation, độ trễ…) | @@LINK 05|`AnswerResult`@@ |
| language detection (vi/en) | Đoán ngôn ngữ câu hỏi từ ký tự tiếng Việt đặc trưng | @@LINK 05|Nhận diện ngôn ngữ@@ |
| cross-lingual retrieval | Câu hỏi tiếng Việt, tài liệu tiếng Anh | @@LINK 05|Truy vấn xuyên ngôn ngữ@@ |
| embedding | Vector số biểu diễn "nghĩa" của một đoạn văn | @@LINK 06|Embedding là gì@@ |
| dimension (768), `model_id` | Số chiều vector; khoá định danh model+kích thước | @@LINK 06|Số chiều@@ |
| normalization, dot product, cosine | Chuẩn hoá vector; tích vô hướng = cosine khi chuẩn; `score = 1 − distance` | @@LINK 06|Đo "giống nhau"@@ |
| vector database (ChromaDB) | Kho lưu vector + tìm kiếm gần đúng; chạy nhúng trong tiến trình | @@LINK 06|Vector database@@ |
| batching, `plan_calls` | Chia text thành các lô (≤ 45 text, nửa ngân sách token/phút) | @@LINK 06|Batching@@ |
| token estimate (`chars/4`) | Ước lượng token để lập kế hoạch quota | @@LINK 06|Ước lượng token@@ |
| embedding cache | Bảng SQLite khoá bằng hash; chỉ gửi phần chưa có | @@LINK 06|`CachingEmbedder`@@ |
| `ChromaVectorStore` | Adapter Chroma: upsert, tìm, kiểm cấu hình khi mở | @@LINK 06|`ChromaVectorStore`@@ |
| HNSW, approximate nearest neighbour | Cấu trúc đồ thị cho tìm gần đúng — nhanh nhưng không xác định tuyệt đối | @@LINK 06|HNSW@@ |
| quota plan | Tính tổng request theo ngày (709 + 859 trên hai ngày) | @@LINK 06|Kế hoạch quota@@ |
| chunk / chunking | Đoạn văn bản được cắt để nhúng và truy xuất | @@LINK 07|Chunking là gì@@ |
| fixed-size chunker (Arm B) | Cửa sổ cố định 1600 ký tự, overlap 200 | @@LINK 07|Arm B@@ |
| header-aware chunker (Arm A) | Cắt theo H2/H3, giữ code/bảng nguyên khối | @@LINK 07|Arm A@@ |
| overlap, atomic block | Phần chồng lấn giữa chunk; khối code/bảng không bị cắt | @@LINK 07|Bước 3–4@@ |
| `display_text` / `embed_text` | Văn bản hiển thị vs văn bản đem đi nhúng (có heading path, bỏ link) | @@LINK 07|Cái gì được lưu@@ |
| `chunk_id`, determinism | `source:config:index:04d` — xác định nên index chạy lại là no-op | @@LINK 07|Xác định và bất biến@@ |
| top-k, over-fetch, dedup (`passage_hash`) | Lấy dư (5+10) rồi khử trùng theo đoạn, giữ 5 | @@LINK 07|Retrieval: top-k@@ |
| refusal gate, threshold 0.686 | Top-1 < ngưỡng → không gọi LLM; ngưỡng = 0.7360 − 0.05 | @@LINK 07|Refusal gate@@ |
| tie-break by `chunk_id` | Phá hoà xác định khi hai chunk cùng điểm | @@LINK 07|"Cùng đầu vào@@ |
| index idempotency | Chỉ nhúng chunk chưa có trong store | @@LINK 05|Use case index@@ |

## D. Sinh câu trả lời và gọi LLM API
| Term | Giải thích | Home |
|---|---|---|
| prompt template, version | Prompt là file có phiên bản (`answer_v2`), không nằm trong code | @@LINK 08|Prompt là một file@@ |
| structured output / JSON mode, schema | Ép model trả JSON đúng khoá; schema là JSON Schema | @@LINK 08|Structured output@@ |
| "insufficient" refusal rule | Model đặt `insufficient=true`; câu trả lời hiển thị là thông báo cố định | @@LINK 08|Luật từ chối@@ |
| `parse_answer_json` | Kiểm kiểu chặt đầu ra của model; sai → `GenerationError` | @@LINK 08|Không tin đầu ra@@ |
| one-pass placeholder rendering | Một lượt `re.sub`; `{}` trong dữ liệu không bị coi là placeholder | @@LINK 08|Ghép prompt@@ |
| passage numbering `[n]` | Đánh số passage 1..k; là khoá liên kết prompt ↔ citation | @@LINK 08|Đánh số passage@@ |
| citation marker, `resolve_citations` | Đọc `[n]` ngoài code; số ngoài 1..k bị bỏ và ghi lại | @@LINK 08|`resolve_citations`@@ |
| excerpt | 300 ký tự đầu của passage, cắt ở ranh giới từ, không thêm "…" | @@LINK 08|`excerpt`@@ |
| uncited sentences | Chỉ số chẩn đoán: câu ≥ 5 từ không có marker | @@LINK 08|Chẩn đoán@@ |
| prompt injection | Văn bản trong dữ liệu chứa lệnh nhắm vào model — repo chưa phòng thủ (corpus cố định) | @@LINK 08|Prompt injection@@ |
| temperature 0 | Giảm phương sai đầu ra; không đảm bảo giống hệt | @@LINK 08|Temperature 0@@ |
| rate limit (RPM/TPM/RPD) | Giới hạn request/phút, token/phút, request/ngày theo project & model | @@LINK 09|Giới hạn tốc độ@@ |
| model pinning | Tên model chỉ trong cấu hình, không `-latest` | @@LINK 09|Chọn model@@ |
| token, thinking token | Đơn vị tính phí/giới hạn; token "suy nghĩ" tính như output | @@LINK 09|Token: prompt@@ |
| failure kinds (`quota`/`unavailable`/`other`) | Ba loại lỗi API dùng chung cho retry, log, GUI | @@LINK 09|Lỗi API thành ba loại@@ |
| sliding-window throttle | Giữ lịch sử 60s; chờ nếu không còn chỗ | @@LINK 09|Throttle cửa sổ trượt@@ |
| retry, exponential backoff, jitter, `Retry-After` | Thử lại với chờ tăng dần + ngẫu nhiên; tôn trọng gợi ý của server; trần 120s | @@LINK 09|Retry với backoff@@ |
| `classify_failure` | Hàm duy nhất biết lỗi nào của SDK là lỗi nhà cung cấp | @@LINK 09|Phân loại lỗi@@ |
| fallback model | Model dự phòng, đúng một lần, ngân sách output riêng | @@LINK 09|Vòng `generate()`@@ |
| `finish_reason` check | `MAX_TOKENS`/rỗng → `GenerationError`, không retry, không fallback | @@LINK 09|Kiểm tra phản hồi@@ |
| key redaction | Che API key ở mọi đường ghi ra | @@LINK 09|Che API key@@ |
| daily quota reset (timezone) | Reset nửa đêm giờ Pacific = 14:00 UTC+7 (PDT) / 15:00 UTC+7 (PST); chủ dự án xác nhận, phần tài liệu Google là `[GENERAL]` | @@LINK 09|Quota theo ngày@@ |
| cost estimate with `null` prices | Ước tính chi phí, không bao giờ đoán giá thiếu | @@LINK 09|Chi phí@@ |

## E. Đánh giá, judge, thống kê, thí nghiệm
| Term | Giải thích | Home |
|---|---|---|
| ground truth | Đáp án chuẩn + nguồn kỳ vọng, viết **trước** khi có index | @@LINK 10|Ground truth phải có trước@@ |
| dev set vs eval set | Bộ chỉnh (6 case) vs bộ báo cáo (36 case) — không được chỉnh trên eval | @@LINK 10|Hai bộ câu hỏi@@ |
| result labels (OD-5) | `correct`, `partially_correct`, `incorrect`, `false_refusal`, `correct_refusal`, `hallucination` | @@LINK 10|Sáu nhãn@@ |
| hit@k, MRR | Có trúng trong top-k không; trung bình `1/hạng` | @@LINK 10|Retrieval metric cơ bản@@ |
| section hit, span overlap | Trúng theo offset ký tự nửa mở, không so tên heading | @@LINK 10|Section hit@@ |
| evidence slot | Nhóm nguồn tương đương; case trúng khi mọi slot có một nguồn | @@LINK 10|Evidence slot@@ |
| lenient vs strict | Có/không tính nguồn thay thế; headline lenient, luôn báo kèm strict | @@LINK 10|Lenient@@ |
| duplicate rule | Section-level tính bản trùng bị loại; source-level thì không | @@LINK 10|Luật trùng lặp@@ |
| evidence hit | Mọi required point có quote nguyên văn trong chunk top-k | @@LINK 10|Evidence hit@@ |
| `map_result` | Bảng ánh xạ xác định từ dữ liệu judge sang nhãn | @@LINK 10|Bảng ánh xạ@@ |
| points-covered | `(yes + 0.5·partial)/số point required` | @@LINK 10|Points-covered@@ |
| denominators (answerable / unanswerable / answered) | Ba mẫu số không được lẫn; record lỗi bị loại và liệt kê | @@LINK 10|Mẫu số@@ |
| freeze (tag + hash + amendment) | Đóng băng bộ câu hỏi; sửa im lặng bị phát hiện | @@LINK 10|Đóng băng@@ |
| threats to validity | Các mối đe doạ tính hợp lệ (ngưỡng chỉnh trên A, judge = model, n nhỏ…) | @@LINK 10|Mối đe doạ@@ |
| bias controls, parallel EN/VI group | Kiểm soát thiên lệch; nhóm song song tách hiệu ứng ngôn ngữ | @@LINK 10|Kiểm soát thiên lệch@@ |
| LLM-as-judge | Dùng LLM chấm đầu ra theo rubric; không phải chân lý | @@LINK 11|Judge là gì@@ |
| answer check / refusal check | Hai kiểu chấm: coverage từng point vs "trình bày nội dung liên quan như đáp án" | @@LINK 11|Hai kiểu kiểm tra@@ |
| strict verdict parse, `judge_error` | Sai một chút là `judge_error`, không đoán | @@LINK 11|Parse **nghiêm ngặt**@@ |
| judgement cache & validity | Khoá `(case, arm, sha256(answer), version)`; hash prompt/model khác → từ chối | @@LINK 11|Cache judgement@@ |
| self-preference bias | Judge có xu hướng ưu ái văn bản giống của chính nó | @@LINK 11|Thiên vị của judge@@ |
| spot-check, Cohen's κ | Người kiểm mù mẫu nhỏ; κ = đồng thuận đã trừ phần ngẫu nhiên (0.688) | @@LINK 11|Spot-check mù@@ |
| paired design | Cùng câu hỏi trên cả hai arm; so mỗi câu với chính nó | @@LINK 12|Thiết kế **ghép cặp**@@ |
| p-value, confidence interval (CI) | Xác suất dữ liệu cực đoan nếu không có khác biệt; khoảng giá trị Δ chấp nhận được | @@LINK 12|p-value và khoảng tin cậy@@ |
| nearest-rank percentile | Phân vị ở hạng `ceil(p/100·n)`, không nội suy | @@LINK 12|Trung bình, trung vị@@ |
| McNemar exact | Kiểm định ghép cặp cho kết quả 0/1 dựa trên các cặp bất đồng | @@LINK 12|McNemar exact@@ |
| Wilcoxon signed-rank exact | Kiểm định ghép cặp cho giá trị liên tục (độ trễ, token) | @@LINK 12|Wilcoxon signed-rank@@ |
| paired bootstrap | Lấy mẫu có hoàn lại **chỉ số cặp**, 10 000 lần, seed 42 → CI | @@LINK 12|Paired bootstrap@@ |
| wording rule | `p ≥ 0.05` → "no statistically reliable difference at n = X", không nêu người thắng | @@LINK 12|Luật diễn đạt@@ |
| statistical power | Cần ≥ 6 cặp bất đồng một phía để p < 0.05; n nhỏ → khó đạt ý nghĩa | @@LINK 12|Vì sao "5–0"@@ |
| multiple comparisons | Chạy nhiều phép thử → dương tính giả; repo không hiệu chỉnh | @@LINK 12|So sánh **nhiều metric**@@ |
| confounder | Yếu tố gây nhiễu không phải chunker (thứ tự chạy, cache) | @@LINK 12|Nhiễu cấu trúc@@ |
| controlled experiment, held-constant | Chỉ đổi chunker; mọi thứ khác giữ hằng và được máy kiểm | @@LINK 13|Câu hỏi của thí nghiệm@@ |
| failure analysis (stages) | Phân loại lỗi theo tầng bằng cây quy tắc có thứ tự | @@LINK 13|Failure analysis@@ |
| discordant case | Case hai arm cho kết quả khác nhau — đọc ở mức chunk | @@LINK 13|Đọc từng ca bất đồng@@ |
| measurement-side error | Lỗi do cách đo (judge, ngưỡng), không phải lỗi hệ thống | @@LINK 13|Lỗi phía **đo lường**@@ |
| honest conclusion | Nói đúng mức dữ liệu cho phép, nêu cả điều **không** kết luận | @@LINK 13|Kết luận trung thực@@ |

## F. Dữ liệu, độ bền, kiểm thử, quy trình
| Term | Giải thích | Home |
|---|---|---|
| JSONL (JSON Lines) | Mỗi dòng một JSON; thêm bản ghi = nối dòng | @@LINK 04|JSON Lines@@ |
| SHA-256 / content hash | Danh tính nội dung; cùng nội dung → cùng hash | @@LINK 04|Hash (SHA-256)@@ |
| idempotent / deterministic / append-only | Chạy nhiều lần như một; cùng vào cùng ra; chỉ thêm | @@LINK 04|Idempotent, xác định@@ |
| `fsync`, torn write | Ghi xuống đĩa thật; dòng cụt do crash được nhận diện và cắt | @@LINK 04|Ghi bền vững@@ |
| "last line wins" (`latest_records`) | Trạng thái hiện tại = bản ghi cuối theo khoá | @@LINK 04|Đọc lại@@ |
| atomic replace (`os.replace`) | Ghi tmp rồi đổi tên — người đọc thấy bản cũ hoặc mới | @@LINK 04|Ghi nguyên tử@@ |
| cache key, float32 BLOB | Khoá = hash(model\|task\|text); vector lưu 4 byte/số | @@LINK 04|Cache embedding@@ |
| commit per provider call | Một transaction mỗi lời gọi trả tiền — không mất kết quả đã trả | @@LINK 04|Không mất tiền@@ |
| resume + manifest check | Từ chối tiếp tục khi thiết lập đổi (`RunConfigMismatch`) | @@LINK 04|Resume có kiểm tra cấu hình@@ |
| UTF-8 + LF | Ép LF (`.gitattributes`) để hash/diff ổn định | @@LINK 04|Nhất quán byte@@ |
| pytest, fixture, `tmp_path` | Test bằng `assert` trần; fixture tiêm bằng tên tham số | @@LINK 14|pytest cơ bản@@ |
| fake vs stub vs mock | Fake = cài đặt đơn giản thật; mock kiểm tương tác | @@LINK 14|Fake, stub, mock@@ |
| `FakeClock`, `FakeEmbedder`, `api_error` | Bộ fake có kịch bản của repo | @@LINK 14|Bộ fake của repo@@ |
| `parametrize` | Một hàm test, nhiều bộ dữ liệu | @@LINK 14|Test theo bảng@@ |
| flaky test | Test đôi khi fail; repo ghi nhận (15/15 pass) thay vì che | @@LINK 14|Test flaky@@ |
| mutation testing | Cố tình phá code để chứng minh test bắt được lỗi; đột biến "sống sót" | @@LINK 14|Mutation testing@@ |
| executor / verifier | Hai vai: người làm và người kiểm độc lập (`99-VERIFY`) | @@LINK 15|Chuỗi tác vụ@@ |
| task ledger, status `verified` | Sổ trạng thái tác vụ; `verified with fixes` chưa đủ để đi tiếp | @@LINK 15|Sổ theo dõi tác vụ@@ |
| "Explain it back" | 3–5 ý chủ dự án phải bảo vệ được khi phỏng vấn | @@LINK 15|Quy tắc chung@@ |
| `dev` / `main` / tag | `dev` tích hợp; `main` ổn định, chỉ merge khi chủ dự án nói; tag đóng băng/nộp | @@LINK 15|Git: nhánh@@ |
| git worktree | Thư mục làm việc thứ hai cho cùng repo, dùng cho phiên song song | @@LINK 15|Git worktree@@ |
| workflow incidents | Các sự cố quy trình thật (subagent bịa xác nhận…) | @@LINK 15|Các sự cố quy trình@@ |
| secret scan | Quét lịch sử git tìm khoá; redaction; `.env` git-ignored | @@LINK 15|Bí mật và bảo vệ khoá API@@ |
| GitNexus impact analysis | Phân tích tác động trước khi sửa symbol | @@LINK 15|GitNexus@@ |
| BM25, RRF (hybrid search) | Tìm theo từ khoá + hợp nhất thứ hạng; **chưa** xây trong repo | @@LINK 16|BM25 và Reciprocal Rank Fusion@@ |
| reranking | Cross-encoder xếp hạng lại ứng viên; thêm khi có bằng chứng cần | @@LINK 16|Reranking@@ |
| parent–child / semantic chunking | Kỹ thuật chunking nâng cao; nhắm vào lỗi "một chunk có đủ đáp án không" | @@LINK 16|Chunking nâng cao@@ |
| query rewriting, HyDE | Viết lại/sinh truy vấn giả trước khi tìm | @@LINK 16|Mở rộng/viết lại truy vấn@@ |
| MMR, metadata filter | Đa dạng hoá kết quả; lọc theo metadata | @@LINK 16|Lọc theo metadata@@ |
