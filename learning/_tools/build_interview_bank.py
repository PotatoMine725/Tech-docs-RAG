"""Collect every '## Interview Q&A' section of the topic files into learning/interview-bank.md (no new content is invented).
    PYTHONDONTWRITEBYTECODE=1 python learning/_tools/build_interview_bank.py
"""
import re
from pathlib import Path

LEARNING = Path(__file__).resolve().parents[1]
PIN = "762b754"

parts = [
    f"# Interview bank — câu hỏi phỏng vấn gom từ các file học\n"
    f"> Commit: {PIN} (tag `v1.0-submission`) · File này được **sinh tự động** từ mục *Interview Q&A* của từng file "
    f"(`_tools/build_interview_bank.py`); không có nội dung mới. Mỗi câu trả lời dẫn `[REPO path:line]` để bạn kiểm chứng; "
    f"hãy luyện trả lời **bằng lời của bạn**, không học thuộc.\n"
]
total = 0
for path in sorted(LEARNING.glob("[0-9][0-9]*-*.md")):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^## Interview Q&A\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        continue
    title = text.splitlines()[0].lstrip("# ").strip()
    body = m.group(1).strip()
    count = len(re.findall(r"^\d+\. ", body, re.M))
    total += count
    parts.append(f"\n## [{path.stem[:3].rstrip('-')}]({path.name}) — {title}\n\n{body}\n")
parts.insert(1, f"> Tổng số câu: **{total}**.\n")
(LEARNING / "interview-bank.md").write_text("\n".join(parts), encoding="utf-8", newline="\n")
print(f"wrote interview-bank.md: {total} questions")
