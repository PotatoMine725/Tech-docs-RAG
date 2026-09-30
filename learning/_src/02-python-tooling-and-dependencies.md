# 02 · Công cụ Python và quản lý phụ thuộc: venv, pip, `pyproject.toml`, src layout, import, biến môi trường, cấu hình pytest
> Commit: 762b754 (tag `v1.0-submission`) · Prerequisites: [01](01-python-for-csharp-devs.md), [01b](01b-python-code-reading-guide.md) · Study time: ~5–6h · Home file của: virtual environment (`.venv`), `pip`/`requirements.txt`, `pyproject.toml` (build-system, dependencies, extras, pytest), `pip install -e ".[dev]"`, src layout, `sys.path`/`PYTHONPATH`, `python -m`, `os.getenv` + `python-dotenv`, đường dẫn theo `PROJECT_ROOT`, `OPENBLAS_NUM_THREADS`, marker `gemini`
> Bài tập chạy được: `learning/_tools/exercises/tooling_scenarios.py` (offline; dùng file tạm chứ **không** đụng file `.env` thật; không mạng, không key).

## Vì sao file này quan trọng trong dự án
Bạn quen `dotnet build`, `.csproj`, NuGet, `appsettings.json`. Python có bản tương ứng nhưng **rời rạc hơn**: môi trường ảo, `pip`, `pyproject.toml`, quy tắc tìm module (`sys.path`), và biến môi trường. Phần lớn lỗi "chạy máy tôi được nhưng máy bạn không" đều nằm ở đây. Repo này có vài **bẫy có thật** đã được ghi lại (ví dụ `pip install -r requirements.txt` **không đủ** để chạy GUI hay pytest; xem 2.3) — hiểu file này giúp bạn tự cài, chạy test, và đọc script mà không bị bất ngờ.

---

## Level 1 — Basic

### 1.1 Virtual environment: `.venv` ≈ một "thư mục packages" riêng cho dự án
- **Ý tưởng:** cài thư viện vào Python **toàn cục** sẽ đụng phiên bản giữa các dự án. `python -m venv .venv` tạo một thư mục chứa một bản Python + `site-packages` **riêng**; kích hoạt (activate) để `python`/`pip` trỏ vào đó.
- **Trong repo này:** README hướng dẫn tạo `.venv` rồi kích hoạt theo shell (PowerShell `.venv\Scripts\Activate.ps1`; Git Bash `source .venv/Scripts/activate`; Linux/Mac `source .venv/bin/activate`). `.venv` bị **git bỏ qua** (`.gitignore`). CLAUDE.md quy định chạy test bằng `.venv/Scripts/python.exe -m pytest`. [REPO README.md:107-114], [REPO .gitignore:153], [REPO CLAUDE.md:12]
- **C# analogy:** không có tương đương trực tiếp: NuGet đặt package trong cache toàn máy và `obj/project.assets.json` khoá phiên bản theo dự án. `.venv` giống "bản sao riêng của cả runtime + thư viện" của dự án.
- **Tại sao:** tái lập môi trường; xoá `.venv` và tạo lại là cách "làm sạch" an toàn.
- **Pitfalls `[GENERAL]`:** quên activate rồi `pip install` sẽ cài vào Python toàn cục. Gọi trực tiếp `.venv/Scripts/python.exe` (như CLAUDE.md) tránh hoàn toàn chuyện đó.

### 1.2 `pip` và `requirements.txt`: danh sách phụ thuộc "phẳng"
- **Ý tưởng:** `pip install -r requirements.txt` cài từng dòng. Mỗi dòng là một **tên package** kèm **ràng buộc phiên bản** (`>=1.4,<2.0`: từ 1.4 nhưng dưới 2.0 — tương đương "cho phép cập nhật minor/patch, chặn major").
@@SNIP requirements.txt 1-6@@
- **Đọc chậm:** `markitdown[pdf,docx]>=0.1.8,<0.2` có **extras** trong ngoặc vuông: cài kèm nhóm phụ thuộc tuỳ chọn tên `pdf` và `docx` của package đó.
- **Mỗi thư viện làm gì (từ CLAUDE.md, stack khoá):** `chromadb` (vector store), `google-genai` (Gemini SDK), `python-dotenv` (đọc `.env`), `PyYAML` (đọc YAML blueprint), `markitdown` (chuyển PDF/DOCX/... sang Markdown, chỉ trong `infrastructure/parsing/`), `PySide6` (GUI). [REPO CLAUDE.md:6]
- **C# analogy:** `<PackageReference Include="X" Version="[1.4,2.0)" />` — khoảng phiên bản cũng dùng ký hiệu `[a,b)` trong NuGet.
- **Tại sao chặn major (`<2.0`):** major mới thường phá API; chặn để bản build cũ còn chạy được.
- **Pitfalls `[GENERAL]`:** `requirements.txt` không có cơ chế "khoá chính xác toàn bộ cây phụ thuộc" (lockfile). Hai lần cài cách nhau vài tháng có thể ra phiên bản phụ thuộc gián tiếp khác nhau.

### 1.3 `pyproject.toml`: metadata dự án ở một chỗ (như `.csproj`)
- **Ý tưởng:** `pyproject.toml` (định dạng TOML) mô tả **build backend**, **metadata dự án**, **phụ thuộc**, và cấu hình công cụ (như pytest). Đây là chuẩn hiện đại; `requirements.txt` là cách cũ/đơn giản.
- **Trong repo này:**
@@SNIP pyproject.toml 1-17@@
- **Đọc chậm:** `[build-system]` nói công cụ dựng gói (`setuptools`); `[project]` có `name`, `version = "0.0.0"`, `requires-python = ">=3.10"` (yêu cầu phiên bản Python tối thiểu), và `dependencies`. Lưu ý `PySide6` **không** ghi phiên bản trong `pyproject.toml`, nhưng `requirements.txt` ghi `PySide6>=6.6,<7.0` — hai file **không hoàn toàn giống nhau** (sự thật quan sát được, không phải sự cố đã ghi).
- **C# analogy:** `<PropertyGroup>` (TargetFramework ≈ `requires-python`) + `<ItemGroup>` với `PackageReference`.
- **Tại sao có cả hai file:** `pyproject.toml` khai báo dự án là **một package cài được** (`knowledge_assistant`); `requirements.txt` là danh sách cài nhanh cho người dùng. Người bảo trì nên giữ hai bên khớp nhau. `[GENERAL]`

---

## Level 2 — Intermediate

### 2.1 Extras tuỳ chọn và `pip install -e ".[dev]"`
@@SNIP pyproject.toml 19-24@@
- **Extras:** `[project.optional-dependencies]` khai báo nhóm `dev = ["pytest"]`. `pip install ".[dev]"` cài dự án **và** nhóm `dev` (ở đây chỉ `pytest`).
- **`-e` (editable install):** thay vì **sao chép** code vào `site-packages`, pip tạo một liên kết trỏ về thư mục nguồn; sửa `.py` là có hiệu lực ngay. `pip install -e ".[dev]"` = "cài dự án hiện tại ở chế độ editable, kèm extras `dev`". [REPO README.md:118]
- **`[tool.setuptools.packages.find] where = ["src"]`:** nói với setuptools tìm package trong thư mục `src/` (xem **src layout** ở 2.2).
- **Đã chạy thử offline** (`tooling_scenarios.py` mục T5): `importlib.metadata.version("knowledge-assistant")` = `0.0.0` và `requires(...)` liệt kê `['PySide6', 'chromadb<2.0,>=1.4', 'google-genai<2.0,>=1.0']` — metadata đọc từ **bản cài trong `.venv`**.
- **C# analogy:** editable install ≈ `ProjectReference` (tham chiếu tới project nguồn) thay vì `PackageReference` tới `.nupkg` đã build.
- **Tại sao:** README ghi rằng `pip install -r requirements.txt` **một mình không đủ** cho lệnh chạy GUI (`python -m knowledge_assistant.presentation.desktop.app`) và cho `pytest` — điều này được kiểm ở QC-001 trên một bản clone mới. [REPO README.md:116-120]
- **Pitfalls `[REAL]`:** lỗi phổ biến của người mới: chỉ chạy `pip install -r requirements.txt` rồi gặp `ModuleNotFoundError: knowledge_assistant`. Cần cài editable để package của **chính dự án** vào được `sys.path`.

### 2.2 **src layout** và cách Python tìm module (`sys.path`)
- **Ý tưởng:** mã nguồn nằm ở `src/knowledge_assistant/...` (không nằm ở gốc repo). Lợi ích: khi chạy test/script từ gốc repo, bạn **không vô tình** import bản chưa cài từ thư mục hiện tại; mọi import phải đi qua `sys.path` được thiết lập có chủ đích.
- **`import` hoạt động thế nào:** Python duyệt `sys.path` (danh sách thư mục) theo thứ tự tìm module. Nguồn của nó: thư mục của script, biến môi trường `PYTHONPATH`, `site-packages` (gồm liên kết editable).
- **Trong repo này có ba cơ chế cùng tồn tại (đều để `import knowledge_assistant` chạy được):**
  1. **Editable install** (`pip install -e`): cho mọi nơi trong `.venv`.
  2. **pytest:** cấu hình `pythonpath = ["src", "."]` — pytest tự thêm hai thư mục vào `sys.path` khi chạy test (thêm `"."` để `from tests.fakes import ...` và `from scripts.evaluation...` hoạt động).
  3. **Script CLI:** mỗi script chèn `src` vào `sys.path` ở đầu file:
@@SNIP scripts/ask.py 65-66@@
  Cả `PROJECT_ROOT = Path(__file__).resolve().parents[1]` — từ đường dẫn file script leo lên **hai cấp** (`scripts/ask.py` → `scripts/` → gốc repo). `parents[0]` là thư mục chứa file, `parents[1]` là cha của nó.
- **Đọc chậm:** `sys.path.insert(0, ...)` đặt thư mục vào **đầu** danh sách, nên bản trong `src` **thắng** mọi bản khác cùng tên.
- **Đã chạy thử offline** (mục T1 và ghi chú cuối): chạy từ gốc worktree với `PYTHONPATH="src;."` → `knowledge_assistant` được import **từ worktree hiện tại**; chạy **không** có `PYTHONPATH` → import ra `D:\Code\Python\Knowledge assistant\src\knowledge_assistant\__init__.py`, tức **checkout chính**, vì editable install của `.venv` trỏ về đó.
- **Pitfalls `[REAL]` (worktree):** khi dùng **git worktree** trong `.claude/worktrees/...` mà **dùng chung `.venv`** của checkout chính, một lệnh Python **không** có `PYTHONPATH`/`pythonpath` sẽ chạy code của **checkout chính**, không phải worktree. Bài này (DISTILL-001) đã đặt `PYTHONPATH="src;."` cho mọi script chạy thử vì lý do đó. Trên Windows dấu ngăn cách của `PYTHONPATH` là `;`, không phải `:`.
- **C# analogy:** `sys.path` ≈ danh sách thư mục probing của assembly loader; `PYTHONPATH` ≈ biến môi trường `DOTNET_...` chỉ đường tới DLL (không hoàn toàn giống, nhưng cùng ý "thêm nơi để tìm").

### 2.3 Chạy code: script, `-m`, và package
- **Hai cách chạy:** `python scripts/ask.py "..."` (chạy một **file**; thư mục file được thêm vào `sys.path`) và `python -m knowledge_assistant.presentation.desktop.app` (chạy **module** theo tên đầy đủ; cần package import được — thường qua editable install). [REPO README.md:138-144]
- **Vì sao GUI chạy bằng `-m`:** file GUI dùng **import tương đối** (`from .workers import QtExecutor`, `from .viewmodels...`); import tương đối chỉ hợp lệ khi file chạy như **một phần của package**, tức qua `-m`. [REPO src/knowledge_assistant/presentation/desktop/app.py:20-34]
- **`if __name__ == "__main__":`** (file 01b) đánh dấu "chỉ chạy khi file được chạy trực tiếp, không phải khi bị import".
- **C# analogy:** `dotnet run --project X` vs gọi `X.dll`; `-m` giống chạy một entry point theo tên assembly.
- **Pitfalls:** chạy `python app.py` từ trong thư mục `desktop/` sẽ lỗi `ImportError: attempted relative import with no known parent package`.

### 2.4 Biến môi trường và `.env`: cấu hình + bí mật
- **Ý tưởng:** cấu hình theo môi trường (đường dẫn, tên model, **API key**) đọc từ **biến môi trường** bằng `os.getenv("TÊN", "giá trị mặc định")`. **Không** hard-code, **không** commit bí mật. [REPO CLAUDE.md:11]
- **Trong repo này:** đọc key và các đường dẫn cấu hình:
@@SNIP src/knowledge_assistant/config.py 33-35@@
  `os.getenv("GEMINI_API_KEY") or None` biến chuỗi rỗng thành `None` (rỗng và không đặt coi như nhau). **Chỉ** đọc key từ môi trường; docstring nhắc "never log or print it".
- **`python-dotenv`:** thư viện nạp một file `.env` (mỗi dòng `TÊN=giá trị`) **vào biến môi trường** của tiến trình. Ứng dụng GUI làm thế trong nhánh "thật" (không phải `--fake`):
@@SNIP src/knowledge_assistant/presentation/desktop/app.py 27-31@@
- **Đọc chậm:** `from dotenv import load_dotenv` nằm **trong** hàm (import trễ; chỉ cần khi chạy thật); `Path(__file__).resolve().parents[4] / ".env"` leo bốn cấp từ file `app.py` lên gốc repo rồi ghép `.env`.
- **Quy tắc bí mật của repo:** `.env` bị git bỏ qua; `.env.example` chỉ chứa **placeholder**; key chỉ nằm trong `.env`/môi trường của bạn. Tôi (khi soạn tài liệu này) **không mở** file `.env` thật; các mục dưới đây dùng một file tạm giả. [REPO .gitignore:151]
- **Đã chạy thử offline** (mục T3–T4, file tạm trong thư mục tạm của hệ điều hành với giá trị giả):
  - `os.getenv("KA_DEMO", "fallback")` → `fallback` khi chưa đặt; sau `os.environ["KA_DEMO"]="from-env"` → `from-env`.
  - `load_dotenv(file)` **không ghi đè** biến môi trường đã có (mặc định `override=False`): file chứa `KA_DEMO=from-file` nhưng giá trị hiện hành vẫn `from-env`; biến chỉ có trong file (`KA_ONLY_IN_FILE`) thì được nạp. Với `override=True` thì `from-file` thắng.
- **C# analogy:** `Environment.GetEnvironmentVariable`, hoặc `IConfiguration` với nguồn "biến môi trường" ưu tiên hơn `appsettings.json`; `User Secrets`/`.env` cho bí mật lúc phát triển.
- **Tại sao thứ tự ưu tiên quan trọng:** trong CI/máy khác, biến môi trường thật (đặt ngoài ứng dụng) phải **thắng** file `.env` cục bộ — `override=False` bảo đảm điều đó.
- **Pitfalls `[GENERAL]`:** đừng `print(os.environ)` để debug (sẽ lộ key). Repo và tài liệu này chỉ nhắc tới `GEMINI_API_KEY` **theo tên**.

### 2.5 Đường dẫn theo gốc repo: không phụ thuộc thư mục làm việc
@@SNIP src/knowledge_assistant/config.py 7-15@@
- **Đọc chậm:** `Path(__file__).resolve().parents[2]` là gốc repo (từ `src/knowledge_assistant/config.py` leo hai cấp); hàm `resolve_project_path` trả đường dẫn **tuyệt đối giữ nguyên**, còn tương đối thì **ghép vào gốc repo** (toán tử `/` của `Path`).
- **Đã chạy thử offline** (mục T2): sau khi `os.chdir` sang thư mục tạm, `resolve_project_path("data/chroma") == PROJECT_ROOT / "data" / "chroma"` vẫn `True`; đường dẫn tuyệt đối vẫn tuyệt đối.
- **Tại sao:** script chạy từ bất kỳ thư mục nào vẫn đọc/ghi đúng file (ADR-0005 D16). Nếu dùng đường dẫn tương đối theo `cwd`, chạy từ nơi khác sẽ ghi dữ liệu vào chỗ lạ.
- **`[REAL]` liên hệ worktree:** các đường dẫn dữ liệu (`CHROMA_PATH`, `CHUNKS_DIR`, `LOGS_DIR`) có thể **ghi đè bằng biến môi trường** để worktree trỏ vào dữ liệu của checkout chính (dữ liệu bị git bỏ qua nên worktree mới không có sẵn). [REPO src/knowledge_assistant/config.py:18-30]
- **C# analogy:** `AppContext.BaseDirectory`/`Path.Combine(root, relative)` thay vì phụ thuộc `Environment.CurrentDirectory`.

---

## Level 3 — Advanced

### 3.1 Cấu hình pytest trong `pyproject.toml`
@@SNIP pyproject.toml 25-31@@
- **Đọc chậm:**
  - `testpaths = ["tests"]`: chỉ tìm test trong `tests/`.
  - `pythonpath = ["src", "."]`: thêm hai thư mục vào `sys.path` (xem 2.2). `"."` cho phép `from tests.fakes import ...` (thư mục `tests` **không có** `__init__.py` nhưng vẫn import được nhờ **namespace package** ngầm của Python 3 — `[GENERAL]`; đã chạy: các script trong `learning/_tools/exercises/` import `tests.fakes` thành công khi `PYTHONPATH` có `.`).
  - `addopts = "-m 'not gemini'"`: **luôn** thêm `-m 'not gemini'` → mọi test đánh dấu `@pytest.mark.gemini` bị **loại** mặc định; đó là cách repo đảm bảo test mặc định **offline**.
  - `markers = [...]`: khai báo marker `gemini` để pytest không cảnh báo; mô tả "requires a real Gemini API key and network access; excluded by default".
- **Kết quả:** README ghi bộ test mặc định "866 passed, 1 deselected" — "1 deselected" chính là test live có marker `gemini`. [REPO README.md:128-129] Chạy test đó phải bỏ marker có chủ đích và **cần key + mạng** — nằm ngoài phạm vi DISTILL-001 (cấm gọi API).
- **C# analogy:** `[Trait("Category","Integration")]` + `dotnet test --filter "Category!=Integration"`; ở đây filter mặc định nằm trong cấu hình.
- **Tại sao `python -m pytest` chứ không `pytest`:** `python -m` thêm **thư mục hiện tại** vào `sys.path` và dùng đúng interpreter của `.venv`; CLAUDE.md quy định dạng lệnh này. [REPO CLAUDE.md:12]
- **Pitfalls `[GENERAL]`:** `pythonpath` là tính năng của pytest ≥ 7; người dùng bản cũ sẽ thiếu. Repo không ghim phiên bản `pytest` (extras chỉ ghi `pytest`).

### 3.2 `OPENBLAS_NUM_THREADS=1` và máy RAM thấp
- **Vấn đề:** `numpy`/ChromaDB dùng thư viện đại số tuyến tính (OpenBLAS) mặc định **đa luồng**; trên máy Windows ít RAM có thể lỗi cấp phát bộ nhớ. README khuyên đặt `OPENBLAS_NUM_THREADS=1` (đã có trong `.env.example`). [REPO README.md:125-126]
- **Trong code:** một script đặt mặc định ngay đầu file **trước khi import numpy/chroma**:
  `os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")` (`setdefault` = chỉ đặt nếu chưa có). [REPO scripts/evaluation/judge_run.py:25]
- **Vì sao phải đặt trước import:** biến được thư viện C đọc **lúc nạp**; đặt sau khi đã import thì vô tác dụng.
- **Trong buổi soạn tài liệu này:** mọi lần chạy Python đều đặt `OPENBLAS_NUM_THREADS=1` và chỉ một tiến trình nặng cùng lúc (ràng buộc của DISTILL-001).
- **C# analogy:** cấu hình `ThreadPool`/`MaxDegreeOfParallelism` để tránh quá tải, nhưng ở đây tác động lên **thư viện native** qua biến môi trường.
- **Pitfalls `[GENERAL]`:** một triệu chứng của thiếu RAM là `MemoryError`/lỗi cấp phát trong `numpy`; giảm số luồng có thể giúp nhưng không thay thế việc đóng bớt ứng dụng.

### 3.3 Cài lại từ đầu: thứ tự và những gì "không có trong git"
Thứ tự README (rút gọn): (1) clone + tạo venv; (2) `pip install -r requirements.txt` rồi `pip install -e ".[dev]"`; (3) cấu hình `.env` (copy từ `.env.example`, điền key **của bạn**); (4) chạy test offline; (5) dựng pipeline từ đầu (chuẩn hoá → chunk → index) **hoặc** dùng index dựng sẵn; (6) hỏi từ CLI; (7) chạy GUI; (8) chạy đánh giá (tốn quota). [REPO README.md:106-150]
- **Những thứ KHÔNG nằm trong git** (git bỏ qua): `.venv`, `.env`, `data/chroma/*` (index) và các file chunk/embedding cache — người clone mới **không có sẵn**; phải dựng lại hoặc trỏ tới bản có sẵn. [REPO .gitignore:227-228]
- **Tại sao:** dữ liệu sinh ra lớn/có thể dựng lại không nên nằm trong git; bí mật thì tuyệt đối không.
- **Pitfalls `[REAL]`:** bước 5 "spends embedding quota unless texts are already cached" — chạy `build_index.py` trên máy mới mà không có cache sẽ **tốn quota thật** (file 06). Trong buổi soạn tài liệu này tôi **không** chạy các bước 5–8.

### 3.4 Phiên bản Python và độ tin cậy của tuyên bố "chạy được"
- **Sự thật kiểm được:** `requires-python = ">=3.10"` (pyproject). README ghi bộ test 866 test được xác minh trên Python 3.13.3 (Windows); bộ 104 test của INGEST-003 chạy trên Linux Python 3.13.12 và 3.11.15; **bộ hiện tại chưa chạy trên Linux**. [REPO README.md:102-104]
- **Tại sao đáng chú ý:** README **giới hạn tuyên bố** đúng mức kiểm thử; nó không nói "chạy mọi nơi". Đây là thói quen tốt khi viết tài liệu kỹ thuật: ghi rõ **đã kiểm ở đâu**.
- **Pitfalls `[GENERAL]`:** `>=3.10` cho phép cú pháp như `str | None` (PEP 604) và `match`; code dùng `str | None` khắp nơi (ví dụ `config.py:33`) nên **không** chạy trên 3.9.

---

## Exercises (offline; đáp án trong `<details>`)

**B1 (Basic).** `chromadb>=1.4,<2.0` cho phép cài những phiên bản nào? Vì sao chặn `<2.0`?
<details><summary>Đáp án</summary>
Từ 1.4 trở lên nhưng **dưới 2.0** (ví dụ 1.4.x, 1.9.x; **không** 2.0). Chặn major để một bản phá API không âm thầm được cài. (`requirements.txt` dòng 1.)
</details>

**B2 (Basic).** Sự khác nhau chính giữa `pip install -r requirements.txt` và `pip install -e ".[dev]"`?
<details><summary>Đáp án</summary>
Cái đầu cài các **thư viện bên thứ ba** trong danh sách; cái sau cài **chính dự án** ở chế độ editable (để `import knowledge_assistant` chạy được) và thêm extras `dev` (pytest). README ghi cái đầu **một mình không đủ** cho GUI/`pytest` ([REPO README.md:116-120]).
</details>

**B3 (Basic).** Vì sao GUI được chạy bằng `python -m knowledge_assistant.presentation.desktop.app` chứ không `python app.py`?
<details><summary>Đáp án</summary>
File dùng **import tương đối** (`from .workers import ...`) chỉ hợp lệ khi file là một phần của package; `-m` chạy nó như module của package. Chạy `python app.py` từ thư mục con sẽ lỗi "attempted relative import with no known parent package" ([REPO src/knowledge_assistant/presentation/desktop/app.py:20-29]).
</details>

**I1 (Intermediate).** Đứng ở gốc repo, `python scripts/ask.py ...` làm sao import được `knowledge_assistant` dù không cần editable install?
<details><summary>Đáp án</summary>
Script tự chèn `PROJECT_ROOT / "src"` vào **đầu** `sys.path` (`sys.path.insert(0, ...)`) trước khi import package ([REPO scripts/ask.py:65-66]).
</details>

**I2 (Intermediate).** Tệp `.env` chứa `X=1` nhưng shell đã có `X=2`. Sau `load_dotenv(path)` (mặc định), `os.getenv("X")` là gì? Nếu `override=True`?
<details><summary>Đáp án</summary>
`"2"` (biến môi trường thật thắng, `override=False`); với `override=True` là `"1"`. Đã chạy thử với file tạm và biến giả `KA_DEMO` (mục T4: `from-env` rồi `from-file`).
</details>

**I3 (Intermediate).** Bạn chạy `python -c "import knowledge_assistant; print(knowledge_assistant.__file__)"` trong một git worktree dùng chung `.venv` với checkout chính, **không** đặt `PYTHONPATH`. Nó in ra đường dẫn ở đâu? Vì sao quan trọng?
<details><summary>Đáp án</summary>
Đường dẫn thuộc **checkout chính** (`D:\Code\Python\Knowledge assistant\src\knowledge_assistant\__init__.py` — đã chạy thử), vì editable install trong `.venv` trỏ về đó. Quan trọng: lệnh chạy **code của checkout chính**, không phải worktree — có thể sai kết quả khi bạn muốn kiểm code ở worktree. Cách xử lý: đặt `PYTHONPATH="src;."` (như các script trong `learning/_tools/exercises/`) hoặc dùng `pythonpath` của pytest.
</details>

**A1 (Advanced).** `addopts = "-m 'not gemini'"` đảm bảo điều gì? Nếu ai đó thêm một test gọi API thật nhưng **quên** đánh dấu `gemini`, điều gì xảy ra?
<details><summary>Đáp án</summary>
Mọi test có marker `gemini` bị loại khỏi lần chạy mặc định. Test **quên** marker sẽ **được chạy mặc định** và gọi API thật (tốn quota/cần key) — marker là **quy ước tự giác**, không phải rào cản kỹ thuật. Repo bù bằng các fake cho mọi adapter và những test như `test_gemini_requires_api_key_and_makes_no_call` (không có key → `ConfigurationError`, số request = 0; [REPO tests/unit/test_gemini_boundary.py:8-13]), cùng quy ước CLAUDE.md rule 8. Test live duy nhất mang marker nằm ở [REPO tests/integration/retrieval/test_gemini_embedding_live.py:30-30] ([REPO pyproject.toml:25-31], [REPO CLAUDE.md:12]).
</details>

**A2 (Advanced).** Viết (giấy) cách bạn kiểm tra rằng một máy mới **không** bị lộ key khi debug cấu hình. Nêu hai điều **không** được làm.
<details><summary>Đáp án</summary>
Nên: chỉ kiểm **có/không** (`bool(os.getenv("GEMINI_API_KEY"))` in `True/False`), hoặc độ dài; dùng `git status`/`.gitignore` để chắc `.env` không bị theo dõi. Không được: `print(os.environ)`/`printenv`/`env` (lộ toàn bộ biến), và không mở/dán nội dung `.env` vào chat/log. Đúng tinh thần quy tắc dự án ([REPO CLAUDE.md:11]).
</details>

**A3 (Advanced).** `PySide6` không có ràng buộc phiên bản trong `pyproject.toml` nhưng có `>=6.6,<7.0` trong `requirements.txt`. Nêu một rủi ro và một cách xử lý.
<details><summary>Đáp án</summary>
Rủi ro: ai chỉ chạy `pip install -e .` (không qua `requirements.txt`) có thể cài một PySide6 quá cũ/mới; hai nguồn có thể lệch dần. Cách xử lý: giữ **một nguồn sự thật** (ràng buộc trong `pyproject.toml`, `requirements.txt` sinh ra từ đó hoặc ngược lại) hoặc thêm kiểm tra CI cho hai file khớp. `[GENERAL]` — đây là quan sát, không phải sự cố đã xảy ra trong repo ([REPO pyproject.toml:10-17], [REPO requirements.txt:1-6]).
</details>

## Self-check questions
1. `.venv` giải quyết vấn đề gì? Nó có nằm trong git không?
2. `requirements.txt` và `pyproject.toml` khác nhau ở vai trò nào?
3. Extras (`[dev]`) và editable install (`-e`) là gì?
4. Ba cơ chế nào làm `import knowledge_assistant` chạy được trong repo?
5. `python script.py` khác `python -m package.module` thế nào?
6. `load_dotenv` mặc định có ghi đè biến môi trường không?
7. `addopts = "-m 'not gemini'"` làm gì?
8. Vì sao `OPENBLAS_NUM_THREADS` phải đặt trước khi import numpy?

## Interview Q&A
1. **"Virtual environment dùng để làm gì?"** — Cô lập phụ thuộc theo dự án để tái lập và tránh xung đột phiên bản ([REPO README.md:107-114]).
2. **"Bạn đảm bảo test không gọi API thật thế nào?"** — Marker `gemini` + `addopts = "-m 'not gemini'"` + fake cho mọi adapter; adapter Gemini không có key thì ném lỗi cấu hình và không gọi mạng ([REPO pyproject.toml:25-31]).
3. **"Bạn quản lý cấu hình và bí mật ra sao?"** — Biến môi trường (`os.getenv`), `.env` git-ignored, `.env.example` chỉ placeholder; key chỉ đọc từ môi trường và không bao giờ in ([REPO src/knowledge_assistant/config.py:33-35]).
4. **"Tại sao dùng src layout?"** — Tránh import nhầm bản chưa cài từ thư mục hiện tại; buộc đi qua cơ chế cài/`sys.path` có chủ đích ([REPO pyproject.toml:22-23]).
5. **"Một lỗi môi trường bạn từng gặp?"** — `pip install -r requirements.txt` không đủ (thiếu editable install) — bắt được ở test clone sạch của QC-001; và worktree dùng chung `.venv` chạy nhầm code checkout chính ([REPO README.md:116-120]).
6. **"Đường dẫn tương đối theo cwd có vấn đề gì?"** — Chạy từ thư mục khác ghi/đọc sai chỗ; repo neo đường dẫn vào `PROJECT_ROOT` ([REPO src/knowledge_assistant/config.py:7-15]).

## Further reading
- Python Packaging User Guide (`https://packaging.python.org`) — `pyproject.toml`, extras, editable installs. `[GENERAL]`
- Python docs: `venv` (`https://docs.python.org/3/library/venv.html`), `site`/`sys.path`. `[GENERAL]`
- pytest docs: *Configuration* (`pytest.ini_options`, `markers`, `pythonpath`). `[GENERAL]`
- python-dotenv docs — hành vi `override`. `[GENERAL]`
- Tiếp theo: [14](14-testing-and-quality.md) (cách viết test với fake) và [15](15-ai-assisted-dev-workflow.md) (worktree, quy trình).
