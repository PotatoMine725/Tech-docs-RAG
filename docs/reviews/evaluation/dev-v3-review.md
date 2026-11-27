# dev-v3 owner review sheet (19 approved, Q3-DEV-011 replaced and pending owner)

Status: **not frozen**. On 2026-11-27 the owner approved 19 questions as written (001-010, 012-020) and asked for 011
(C2-07 title page, too thin) to be replaced. The new 011 is `review_status: draft` and waits for the owner's check.
Make no index, retrieval, LLM or judge runs on these questions until the owner approves 011 and tags `dev-freeze-v3`.

Purpose: 20 dev-split questions (tuning only, never reported). They are for calibrating the system's refusal
threshold (dense-score gate plus LLM refusal, `docs/plans/local-llm-preregistration.md` §6) and for re-measuring
language detection (`src/knowledge_assistant/application/common/language.py`), including Vietnamese typed without
diacritics.

Sources: `data/evaluation/questions/dev-v3.jsonl` is built from `drafts-v3/dev-v3.yaml` by
`scripts/evaluation/build_questions_v3.py`. Absence proofs are in `evidence-map-v3.yaml`. The checks are in
`scripts/evaluation/validate_questions_v3.py`.

## How to review
Write `ok` or `change: <what>` in the last column of each row. Your cells survive a refresh of the table
(`.venv/Scripts/python.exe scripts/evaluation/build_review_sheet_v3.py`). Once every row is `ok` (or has been fixed),
the drafts get `review_status: approved` and the owner tags `dev-freeze-v3`.

## Composition (as built)
| Group | Count | IDs |
|---|---|---|
| Corpus 1 (EN docs), question en, answerable | 3 | 001-003 |
| Corpus 1, question vi, answerable (1 without diacritics: 005) | 3 | 004-006 |
| Corpus 2 VI docs, question vi, answerable (2 without diacritics: 008, 010) | 4 | 007-010 |
| Corpus 2 mixed VI-EN doc (C2-04), question vi, answerable (replacement 011, see below) | 1 | 011 |
| Corpus 2 EN docs, question en, answerable | 2 | 012-013 |
| Corpus 2 mixed VI-EN doc (C2-04), mixed VI-EN question, answerable | 1 | 014 |
| Near corpus 1, unanswerable (1 en, 1 vi) | 2 | 015-016 |
| Near corpus 2, unanswerable (vi, vi without diacritics, en, mixed) | 4 | 017-020 |

Totals: 14 answerable and 6 unanswerable. No document is expected by more than 2 questions. Difficulty: 3 easy,
11 medium, 6 hard (unanswerable rows included). Three questions are paraphrased, with little word overlap with the
source (001, 003, 008). They are marked `paraphrase` in `retrieval_challenges`.

A mixed VI-EN question has `language: vi`, the answer language, and `question_language: mixed`. The record schema
only allows en / vi for `language`.

## Checks (validate_questions_v3.py: OK, 0 errors)
- **Quotes:** all 29 evidence quotes are substrings of their section after NFC and whitespace collapsing on both sides.
  Corpus-2 quotes come from prose only (no `|`).
- **Zero hits:** all 20 absence terms have 0 hits in all 48 accepted documents (24 in corpus 1, 24 in corpus 2). Each term
  is matched as written and with diacritics folded away (`đ` becomes `d`, tone and shape marks are dropped).
- **No eval-section overlap:** no row expects a section (source + heading path) that an eval-v1 or eval-v2 case
  expects or accepts. No question text repeats a v1 or v2 question. The highest word overlap (Jaccard) with any
  v1 or v2 question is 0.379 (012 vs Q2-EVAL-039: same document, different use case). The error limit is 0.5.
- **v1/v2 unchanged:** the v1 and v2 builders were re-run, and `eval-v1`, `dev-v1`, `eval-v2`, `dev-v2` (.jsonl),
  `evidence-map.yaml` and `evidence-map-v2.yaml` are byte-identical to the versions in dev.
- **Converted text:** corpus 2 was re-converted from `corpus2/incoming` into a scratch folder and matches every
  `converted_sha256` in the manifest. The main checkout's `corpus2/converted` is stale: `C2-21.md` predates erratum
  5ca88e2. Re-run `scripts/corpus2/convert_corpus2.py` there before the next v2/v3 validation.

## Things worth a look
- Rule 5 left little room in the corpus-2 VI docs. C2-10, 11, 24, 25, 29, 30 and 32 are one whole-document section
  each, and eval-v2 expects every one of them. The large section of C2-07 is eval-expected too. The five VI-doc
  questions used C2-16 (2), C2-26 (2) and the C2-07 title page (011, a thin "who wrote this" fact).
- **Replacement 011 (2026-11-27, pending owner):** the owner rejected the title-page question. No corpus-2 VI-doc
  section is free (C2-16 and C2-26 already have 2 questions each; the rest is eval-expected), so, as the owner's
  instruction allowed, the slot moved to the mixed VI-EN doc C2-04: section `4. Cơ chế Định danh & Động lực Kinh tế
  của Creator`, which no eval or dev case expects and whose text is not in the near-duplicate C2-22. The question is
  Vietnamese with diacritics, medium. The corpus-2 VI-doc count is therefore 4, not 5; mixed docs carry 2 (011, 014).
- The C2-26 formulas are images. 009 and 010 use the only formulas written as text. In 010 the source writes
  `120.103.(1-α)M0`, probably 120·10³ after conversion. The expected answer quotes it as written.
- 007 was reworded so that it does not echo Q2-DEV-001 (same slides, causes vs atypical forms).
- 018: `HCV` alone appears in C2-28, but only as part of `HCVC` (hội chứng vành cấp), so it is not an absence term.
- **Language check (report only, detector not tuned):** `detect_language` labels 19 of 20 questions correctly.
  **Mismatch:** 010 (vi, typed without diacritics) is detected as `en`. Its ASCII words are mostly not in the
  detector's word list. The mixed questions 014 and 020 are detected as `vi`, as labelled.

## Cases
<!-- CASES START -->
| ID | Lang · typing · difficulty | Question | Expected answer (one line) | Source · heading path | Evidence quote(s) | owner: ok / change |
|---|---|---|---|---|---|---|
| Q3-DEV-001 | en · en · medium | A reviewer complained that my unit tests are full of unexplained literal values. Why is that a problem, and what should I do with those values instead? | Such hard-coded "magic strings" make tests less readable and harder to maintain, and make readers wonder why a value was chosen (pulling them into implementation details); assign the hard-coded values to constants to express intent. | #03 Unit testing best practices for .NET > Best practices > Avoid magic strings | [P1] "These values make your code less readable and harder to maintain."<br>[P2] "Rather than using magic strings, assign any hard-coded values to constants." | ok (owner 2026-11-27) |
| Q3-DEV-002 | en · en · hard | In C#, after `object boxed = "text";`, what are the compile-time and run-time types of `boxed`, and which of those two types decides virtual method dispatch? | The compile-time type is `object` and the run-time type is `string`. The run-time type controls virtual method dispatch (and `is` / `switch` expressions); the compile-time type controls overload resolution and available conversions. | #26 The C# type system > Compile-time type and run-time type | [P1] "In the preceding example, `boxed` has a compile-time type of `object` but a run-time type of `string`."<br>[P2,P3] "The compile-time type controls overload resolution and available conversions. The run-time type controls virtual method dispatch, `is` expressions, and `switch` expressions." | ok (owner 2026-11-27) |
| Q3-DEV-003 | en · en · medium | How can I put a set of minimal API endpoints under one shared URL prefix and require authorization for all of them at once, instead of configuring each endpoint separately? | Use the `MapGroup` extension method: it organizes endpoints under a common prefix and lets you customize the whole group with a single call, e.g. `RequireAuthorization` (or `WithMetadata`) on the group. | #23 Routing in ASP.NET Core > Route groups | [P1] "extension method helps organize groups of endpoints with a common prefix and reduces repetitive code."<br>[P2] "Use this method to customize entire groups of endpoints with a single call to methods like [RequireAuthorization]" | ok (owner 2026-11-27) |
| Q3-DEV-004 | vi · diacritics · medium | Service mình đăng ký vào DI container của ASP.NET Core có implement IDisposable. Vậy ai sẽ gọi Dispose cho nó, và mình có nên tự gọi Dispose cho service lấy từ container không? | Container tự gọi Dispose cho các kiểu IDisposable mà nó tạo ra (kể cả singleton); service lấy từ container thì developer không bao giờ được tự dispose. | #10 Dependency injection in ASP.NET Core > Design services for dependency injection > Disposal of services | [P1] "The container calls [Dispose](/en-us/dotnet/api/system.idisposable.dispose) for the [IDisposable](/en-us/dotnet/api/system.idisposable) types it creates."<br>[P2] "Services resolved from the container should never be disposed by the developer." | ok (owner 2026-11-27) |
| Q3-DEV-005 | vi · no_diacritics · easy | Trong C#, mot class co the ke thua tu bao nhieu base class, va lop dan xuat co duoc ke thua constructor cua lop cha khong? | Một class chỉ kế thừa từ một base class (nhưng có thể implement nhiều interface); lớp dẫn xuất kế thừa mọi thành viên của base class trừ constructor. | #07 C# classes > Inheritance | [P1,P2] "A class can inherit from one base class and implement multiple interfaces. Derived classes inherit all members of the base class except constructors." | ok (owner 2026-11-27) |
| Q3-DEV-006 | vi · diacritics · hard | Trong integration test ASP.NET Core, làm sao để HttpClient tạo từ WebApplicationFactory không tự động đi theo redirect? | Tạo một WebApplicationFactoryClientOptions với AllowAutoRedirect = false và truyền nó vào CreateClient() của factory. | #17 Integration tests in ASP.NET Core > Client options | [P1] "Create the `WebApplicationFactoryClientOptions` class and pass it to the [CreateClient()]"<br>[P2] "AllowAutoRedirect = false" | ok (owner 2026-11-27) |
| Q3-DEV-007 | vi · diacritics · easy | Theo bài giảng, đông đặc phổi thể không điển hình có những dạng gì? | Đông đặc một diện rộng, đông đặc khu trú (thể trung tâm), đông đặc rải rác và đông đặc co kéo. | #C2-16 2.2. HC đông đặc phổi không điển hình: | [P1] "Đông đặc một diện rộng"<br>[P1] "Đông đặc khu trú (thể trung tâm)"<br>[P2] "Đông đặc rải rác"<br>[P2] "Đông đặc co kéo" | ok (owner 2026-11-27) |
| Q3-DEV-008 | vi · no_diacritics · medium | Tren phim X-quang nguc, vung phoi bi dong dac trong nhu the nao va co the keo cac cau truc lan can ra sao? | Đám mờ chiếm một vùng, rải rác trên phế trường, một phân thùy hoặc một bên phổi; mật độ đều hoặc không, ranh giới rõ hoặc không. Có thể co kéo cơ hoành, trung thất, các khoảng liên sườn (đông đặc co rút). | #C2-16 3. Triệu chứng X-quang | [P1] "Đám mờ chiếm 1 vùng/rải rác trên phế trường/ 1 phân thuỳ/1 bên phổi. Mật độ đều/không, ranh giới rõ/không."<br>[P2] "Tạng lân cận: co kéo cơ hoành, trung thất, các khoảng liên sườn (đông đặc co rút)." | ok (owner 2026-11-27) |
| Q3-DEV-009 | vi · diacritics · hard | Với động cơ đánh lửa cưỡng bức, tỷ số giãn nở sớm ρ và tỷ số giãn nở sau δ được lấy bằng bao nhiêu? | Với động cơ đánh lửa cưỡng bức, ρ = 1 và δ = ε (bằng tỷ số nén); với động cơ Diesel thì hai tỷ số này phải tính theo công thức. | #C2-26 Tính toán các thông số của chu trình: > Tính quá trình giản nở: | [P1] "ρ = 1 (động cơ đánh lửa cưỡng bức)"<br>[P2] "δ = ε (động cơ đánh lửa cưỡng bức)" | ok (owner 2026-11-27) |
| Q3-DEV-010 | vi · no_diacritics · hard | Ton that nhiet do chay khong hoan toan Delta QH duoc tinh the nao voi dong co Diesel va dong co danh lua cuong buc? | Động cơ Diesel (α > 1): Δ QH = 0. Động cơ đánh lửa cưỡng bức (α &lt; 1): Δ QH = 120.103.(1-α)M0 (theo đúng cách viết của tài liệu, tức 120·10³·(1-α)·M0). | #C2-26 Tính toán các thông số của chu trình: > Tính quá trình cháy | [P1] "α>1 thì Δ QH = 0 (động cơ Diesel)"<br>[P2] "α &lt;1 thì Δ QH = 120.103.(1-α)M0 (động cơ đánh lửa cưỡng bức)" | ok (owner 2026-11-27) |
| Q3-DEV-011 | vi · diacritics · medium | Trong dự án AI Review, làm sao hệ thống ngăn một kênh mạng xã hội bị nhiều Creator nhận chéo hoặc giả mạo, và hồ sơ Creator được duyệt qua những trạng thái nào? | Cột platform_handle trong bảng creator_accounts (ví dụ tiktok:tech_review) là duy nhất toàn hệ thống, nên một kênh không thể bị nhận chéo hay giả mạo; hồ sơ Creator đi qua cổng phê duyệt pending -> active -> suspended. | #C2-04 **BÁO CÁO CHIẾN LƯỢC KINH DOANH VÀ KIẾN TRÚC KỸ THUẬT TỐI ƯU HÓA CHI PHÍ & LỢI NHUẬN** > **PHẦN I: TỔNG QUAN CHIẾN LƯỢC KINH DOANH & MÔ HÌNH TÀI CHÍNH** > **4. Cơ chế Định danh & Động lực Kinh tế của Creator (Creator Identity & Economics)** | [P1] "là duy nhất toàn hệ thống để chống nhận kênh chéo hoặc giả mạo."<br>[P2] "Quản lý trạng thái pending -> active -> suspended." | replaced 2026-11-27, pending owner |
| Q3-DEV-012 | en · en · medium | In FA Management, what status must a class have before it can be closed, and what does the system do when the class is closed? | The class's [Status] must be "Pending for review". On closing, the system sets [Status] to "Closed", appends a "Closed by &lt;user>" line with the date time to [History], saves, returns to the listing screen and emails the FA Manager. | #C2-13 Use Case Specifications > Class Management > UC 18: Close a finished Class | [P1] "The value of [Status] filed is equal to “Pending for review”."<br>[P2] "Update the value of [Status] filed as “Closed”."<br>[P3] "Send email to FA Manager as Sending email to FA Manager after a Class is closed." | ok (owner 2026-11-27) |
| Q3-DEV-013 | en · en · hard | A trainee's Not Attendance Rate is 25%. What Disciplinary Point does FA Management assign? | 60%: the rule is that if 20% &lt; Not Attendance Rate ≤ 30%, [Disciplinary Point] is set to "60%". | #C2-13 Use Case Specifications > Trainee Management > UC 32: Calculate Disciplinary Point | [P1] "If 20% &lt; Not Attendance Rate ≤ 30%, set the value of [Disciplinary Point] field as “60%”." | ok (owner 2026-11-27) |
| Q3-DEV-014 | mixed · diacritics · medium | Trong pilot 30 ngày của AI Review Content Factory, North Star Metric là gì và core hypothesis cần validate là gì? | North Star Metric là Attributed Affiliate Revenue (doanh thu chuyển đổi đo được và quy gán đúng nguồn video); giả thuyết cốt lõi là liệu một AI Product (Merchant) có sẵn sàng dùng mạng lưới Creator được hỗ trợ bởi video AI để tạo lưu lượng có chuyển đổi trả phí (Paid Conversion) hay không. | #C2-04 **BÁO CÁO CHIẾN LƯỢC KINH DOANH VÀ KIẾN TRÚC KỸ THUẬT TỐI ƯU HÓA CHI PHÍ & LỢI NHUẬN** > **PHẦN I: TỔNG QUAN CHIẾN LƯỢC KINH DOANH & MÔ HÌNH TÀI CHÍNH** > **1. Vấn đề thị trường và Giả thuyết kiểm chứng của Pilot (PRD §52)** | [P1] "Attributed Affiliate Revenue"<br>[P2] "Một AI Product (Merchant) có sẵn sàng sử dụng mạng lưới Creator được hỗ trợ bởi video AI để tạo ra lưu lượng truy cập có chuyển đổi trả phí (Paid Conversion) hay không?" | ok (owner 2026-11-27) |
| Q3-DEV-015 | en · en · medium | In EF Core, how do I run a raw SQL query with FromSqlRaw and pass parameters safely so it is not open to SQL injection? | Refuse (not in the documents). Must not claim: FromSqlRaw / FromSqlInterpolated usage or parameter syntax presented as from the documents. | — (not in the documents; near: #22) | ABS3-001: zero hits for `FromSqlRaw`, `FromSql`, `SqlQuery`, `raw SQL`, `ExecuteSql` | ok (owner 2026-11-27) |
| Q3-DEV-016 | vi · diacritics · medium | Trong xUnit, làm sao dùng ICollectionFixture cùng [CollectionDefinition] để nhiều class test chia sẻ chung một database fixture? | Refuse (not in the documents). Must not claim: ICollectionFixture / [Collection] attribute usage presented as from the documents. | — (not in the documents; near: #17, #28) | ABS3-002: zero hits for `ICollectionFixture`, `CollectionDefinition`, `collection fixture` | ok (owner 2026-11-27) |
| Q3-DEV-017 | vi · diacritics · easy | Tràn khí màng phổi được chẩn đoán trên phim X-quang ngực dựa vào những hình ảnh nào? | Refuse (not in the documents). Must not claim: Consolidation X-ray signs presented as pneumothorax signs.; Any pneumothorax sign presented as from the documents. | — (not in the documents; near: #C2-16) | ABS3-003: zero hits for `tràn khí màng phổi`, `pneumothorax` | ok (owner 2026-11-27) |
| Q3-DEV-018 | vi · no_diacritics · medium | Xet nghiem anti-HCV duong tinh co nghia la benh nhan dang bi viem gan C man tinh khong? | Refuse (not in the documents). Must not claim: HBV marker rules applied to anti-HCV as if from the documents. | — (not in the documents; near: #C2-29) | ABS3-004: zero hits for `anti-HCV`, `viêm gan C`, `hepatitis C` | ok (owner 2026-11-27) |
| Q3-DEV-019 | en · en · medium | How do I add online multiplayer to my Unity game with Netcode for GameObjects and a NetworkManager? | Refuse (not in the documents). Must not claim: NetworkManager / NetworkObject setup steps presented as from the documents. | — (not in the documents; near: #C2-19, #C2-27) | ABS3-005: zero hits for `Netcode`, `NetworkManager`, `multiplayer` | ok (owner 2026-11-27) |
| Q3-DEV-020 | mixed · diacritics · hard | Làm sao validate một file XML theo XSD schema bằng XmlSchemaSet và XmlReaderSettings trong C#? | Refuse (not in the documents). Must not claim: XmlReaderSettings.ValidationType / Schemas usage presented as from the documents. | — (not in the documents; near: #C2-08) | ABS3-006: zero hits for `XmlSchemaSet`, `XSD`, `XmlReaderSettings`, `XML Schema` | ok (owner 2026-11-27) |
<!-- CASES END -->
