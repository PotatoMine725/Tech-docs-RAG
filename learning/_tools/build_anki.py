"""Build learning/anki-cards.tsv from glossary.md and the Interview Q&A sections (no new facts are invented).
Cards: glossary term -> explanation + home link; interview question -> the file's model answer.
Anki import: File > Import, separator Tab, HTML on (header lines below set this).
    PYTHONDONTWRITEBYTECODE=1 python learning/_tools/build_anki.py
"""
import html
import re
from pathlib import Path

L = Path(__file__).resolve().parents[1]


def h(md: str) -> str:
    t = html.escape(re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md).strip(), quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    return t.replace("\t", " ").replace("\n", "<br>")


cards = []
section = ""
for line in (L / "glossary.md").read_text(encoding="utf-8").splitlines():
    if line.startswith("## "):
        section = re.sub(r"[^\w]+", "_", line[3:].split(".")[0].strip()) or "glossary"
    m = re.match(r"^\| (.+?) \| (.+?) \| (.+?) \|$", line)
    if m and not line.startswith("| Term") and not line.startswith("|---"):
        term, expl, home = m.groups()
        cards.append((h(term), h(expl) + "<br><small>" + h(home) + "</small>", f"glossary group_{section}"))

for path in sorted(L.glob("[0-9][0-9]*-*.md")):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^## Interview Q&A\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        continue
    num = path.name.split("-")[0]
    for q in re.finditer(r'^\d+\. \*\*"?(.+?)"?\*\* — (.+?)(?=^\d+\. |\Z)', m.group(1), re.S | re.M):
        cards.append((h(q.group(1)), h(q.group(2)), f"interview file_{num}"))

out = ["#separator:tab", "#html:true", "#tags column:3", "#columns:Front\tBack\tTags"]
out += ["\t".join(c) for c in cards]
(L / "anki-cards.tsv").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print(len(cards), "cards")
