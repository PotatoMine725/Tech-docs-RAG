# 00 · Lộ trình học Knowledge Assistant (README chính)
> Commit: 762b754 (tag `v1.0-submission`) · Bộ tài liệu tiếng Việt (giữ thuật ngữ tiếng Anh) để một sinh viên IT năm cuối biết C#/.NET nhưng mới với Python/RAG/LLM có thể **đọc hiểu, giải thích và bảo vệ** dự án này. Nguồn sự thật tiến độ: `_progress.md`; câu hỏi còn mở: `_open-questions.md`.

## Cách dùng
- Mỗi file chủ đề có: header (commit ghim, prerequisites, thời gian học) → **Vì sao quan trọng** → **Level 1 Basic → Level 2 Intermediate → Level 3 Advanced** (mỗi khái niệm: Ý tưởng · C# analogy · *Trong repo này* (ref + trích nguyên văn) · Tại sao · Pitfalls) → **Exercises** B/I/A (đáp án trong `<details>`) → **Self-check** → **Interview Q&A** → **Further reading**.
- **Nhãn bằng chứng:** `[REPO path:dòng]` đã kiểm ở commit ghim; `[GENERAL]` kiến thức chung (tự kiểm lại trước khi dùng); `[REAL]` sự cố thật của dự án (luôn nêu trước trong Pitfalls); `[UNVERIFIED]` chưa xác nhận (liệt kê ở `_open-questions.md`).
- **Khối code có dòng `path:a-b`** là **trích nguyên văn** từ repo (≤ 25 dòng). Chạy `check_refs.py` để chứng minh: nó đối chiếu từng đoạn trích và từng `path:dòng` với **bản git tại commit ghim** (không phải bản trên đĩa).
- Mỗi khái niệm có **một** file "nhà"; file khác chỉ link về. Tra thuật ngữ ở [glossary.md](glossary.md); luyện phỏng vấn ở [interview-bank.md](interview-bank.md) (gom tự động từ các file, không thêm nội dung).
- **Bài tập có chạy code** dùng script trong `_tools/exercises/` (offline, không mạng, không API key). Trong worktree đặt `PYTHONPATH=src;.` (Windows dùng `;`), ví dụ: `.venv\Scripts\python.exe learning\_tools\exercises\judge_stats_scenarios.py`. Bài tập "đã chạy thử" trong tài liệu nghĩa là tôi **thực sự chạy** script đó và ghi lại kết quả.

## Thứ tự đọc và thời gian
| # | File | Nội dung | ~Giờ |
|---|---|---|---|
| 1 | [01b-python-code-reading-guide.md](01b-python-code-reading-guide.md) | **Đọc hiểu** code Python: quy trình 6 bước, bảng giải mã ký hiệu, ~22 template, drill | 4–5 |
| 2 | [01-python-for-csharp-devs.md](01-python-for-csharp-devs.md) | Cú pháp/idiom Python có trong repo, đối chiếu C# | 8–10 |
| 3 | [02-python-tooling-and-dependencies.md](02-python-tooling-and-dependencies.md) | venv, pip, `pyproject.toml`, src layout, `.env`, pytest config | 5–6 |
| 4 | [03-architecture-and-gui.md](03-architecture-and-gui.md) | Layers, ports & adapters, composition root, architecture test, MVVM + Qt thread | 8–10 |
| 5 | [04-data-io-and-reliability-patterns.md](04-data-io-and-reliability-patterns.md) | JSONL, append-only, hash, cache, idempotent, resume | 8–10 |
| 6 | [05-rag-fundamentals.md](05-rag-fundamentals.md) | Toàn bộ pipeline, theo dấu một câu hỏi thật | 7–9 |
| 7 | [06-embeddings-and-vector-search.md](06-embeddings-and-vector-search.md) | Embedding, cosine, Chroma, batch, cache SQLite, quota | 8–10 |
| 8 | [07-chunking-and-retrieval.md](07-chunking-and-retrieval.md) | Arm A vs Arm B, khử trùng, over-fetch, gate | 9–11 |
| 9 | [08-generation-and-prompting.md](08-generation-and-prompting.md) | Prompt có phiên bản, structured output, citation, prompt injection | 8–10 |
| 10 | [09-llm-api-engineering.md](09-llm-api-engineering.md) | Rate limit, retry/backoff, fallback, lỗi, token, chi phí | 9–11 |
| 11 | [10-evaluation-design.md](10-evaluation-design.md) | Bộ câu hỏi, freeze, luật hit, metric, mẫu số, validity | 10–12 |
| 12 | [11-llm-as-judge.md](11-llm-as-judge.md) | Judge, parse chặt, cache, spot-check, Cohen's κ | 8–10 |
| 13 | [12-statistics-for-experiments.md](12-statistics-for-experiments.md) | McNemar, Wilcoxon, bootstrap, phân vị, power | 8–10 |
| 14 | [13-case-study-exp-001.md](13-case-study-exp-001.md) | Thí nghiệm A vs B từ giả thuyết đến kết luận trung thực | 7–9 |
| 15 | [14-testing-and-quality.md](14-testing-and-quality.md) | pytest, fake, flaky, mutation testing | 7–9 |
| 16 | [15-ai-assisted-dev-workflow.md](15-ai-assisted-dev-workflow.md) | Executor/verifier, ledger, worktree, sự cố quy trình, bí mật | 6–8 |
| 17 | [16-beyond-this-project.md](16-beyond-this-project.md) | Lộ trình mở rộng (hybrid/RRF, rerank, đánh giá nâng cao, an toàn) | 6–8 |
| ∗ | [glossary.md](glossary.md) · [interview-bank.md](interview-bank.md) | Tra cứu thuật ngữ · ngân hàng câu phỏng vấn | — |

Tip: đọc 01 và 01b song song (01 dạy khái niệm, 01b dạy **cách đọc**). Tổng ~126–158 giờ (cộng các ô trong bảng); đọc kỹ file 05 trước khi sang 06–13 vì chúng dựa trên pipeline.

## Kế hoạch 8 tuần (gợi ý)
| Tuần | Mục tiêu | File |
|---|---|---|
| 1 | Đọc hiểu code Python; chạy được test offline | 01b, 01, 02 |
| 2 | Kiến trúc và mẫu độ bền dữ liệu | 03, 04 |
| 3 | Pipeline RAG, embedding, vector store | 05, 06 |
| 4 | Chunking, truy xuất, sinh câu trả lời | 07, 08 |
| 5 | Gọi API bền vững, kiểm thử | 09, 14 |
| 6 | Thiết kế đánh giá, LLM judge | 10, 11 |
| 7 | Thống kê và ca nghiên cứu | 12, 13 |
| 8 | Quy trình làm việc + một thử nghiệm nhỏ tự chọn từ file 16 | 15, 16 |

Mỗi tuần: đọc → làm bài tập B/I trước, A sau → tự trả lời Self-check **không nhìn** → luyện 2–3 câu Interview Q&A **bằng lời của bạn**.

## Bạn nên bảo vệ được điều gì khi phỏng vấn (rút gọn)
1. **Vì sao kiến trúc phân lớp + fake** cho phép 866 test offline chạy ~13 giây (file 03, 14).
2. **Hai lớp từ chối** (cổng ngưỡng + `insufficient` của LLM) và vì sao lỗi không bao giờ được đổi thành "insufficient" (05, 08).
3. **Chunking A vs B** và một kết luận trung thực: không khác biệt answer-level đáng tin ở n = 31, chỉ chi phí token khác (07, 13).
4. **Đánh giá không tự lừa mình:** freeze bằng hash, dev/eval tách, mẫu số rõ ràng, judge chỉ cấp dữ liệu, spot-check mù (10, 11).
5. **Retry/backoff/fallback** và cách kiểm thử chúng bằng đồng hồ giả (09, 14).
6. **AI hỗ trợ có kiểm soát:** executor/verifier, nhật ký trung thực, subagent chỉ khám phá chỉ-đọc (15).

## Công cụ trong `_tools/` (chỉ đọc repo; ghi duy nhất vào `learning/`)
| Công cụ | Việc |
|---|---|
| `expand_snippets.py` | Sinh `learning/NN-*.md` từ `_src/`: thay `@@SNIP path a-b@@` bằng trích nguyên văn từ **bản git ở commit ghim** (từ chối > 25 dòng và file chưa theo dõi) |
| `expand_links.py` | Sinh `glossary.md`: mỗi `@@LINK NN\|từ khoá@@` phải khớp đúng một tiêu đề, không thì lỗi |
| `build_interview_bank.py` | Gom mục *Interview Q&A* thành `interview-bank.md` |
| `check_refs.py` | Kiểm: đoạn trích = dòng tại commit ghim; mọi `path:dòng` trong phạm vi và được theo dõi; file chủ đề có ghim `762b754` |
| `exercises/*.py` | Kịch bản offline cho bài tập: retry, sinh câu trả lời, metric đánh giá, judge/thống kê, lưu trữ, tooling, đột biến, RRF |

Quy trình cập nhật một file: sửa `_src/NN-*.md` → `expand_snippets.py` → `expand_links.py` → `build_interview_bank.py` → `check_refs.py` (phải báo 0 vấn đề).

## Giới hạn trung thực của bộ tài liệu
- **Đã chạy thật (offline):** bộ test đầy đủ **một lần** (`866 passed, 1 deselected in 13.27s`, Windows, commit ghim); các kịch bản bài tập; `test_project_structure.py` cùng hai đột biến trên bản sao ngoài repo (file 03); ba đột biến + một lần đối chứng cho phần lưu trữ, trên bản sao ngoài repo (file 14).
- **Không làm (theo ràng buộc):** không gọi Gemini/API, không chạy `ask.py`, `run_eval.py`, `judge_run.py`, dựng index, GUI, hay `compare_arms.py`; không mở `.env`; không sửa mã, test, cấu hình, corpus, dữ liệu, `validation/`.
- **Số liệu thí nghiệm** (file 10–13) lấy từ **báo cáo/snapshot đã có trong repo**; tôi tái tạo được phần thống kê bằng code (McNemar, κ, bảng percentile) nhưng **không chạy lại thí nghiệm**. Dữ liệu chunk nằm ngoài git (git-ignored) nên số 733/859 và tỉ lệ cắt code fence được đối chiếu với tài liệu có trong repo, không tái sinh.
- **Chưa kiểm được:** cách tài nguyên bên ngoài phản ứng (giới hạn Gemini thật, giờ reset quota) — xem `_open-questions.md`.
- **`anki-cards.tsv`:** tạm hoãn theo yêu cầu của chủ dự án.
- **Chưa commit:** mọi thứ nằm trong `learning/` của worktree `learning/distill`; chờ chủ dự án cho phép commit.
