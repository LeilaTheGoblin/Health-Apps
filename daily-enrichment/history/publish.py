#!/usr/bin/env python3
"""
Publish one daily history piece for daily-enrichment/history.html.

Usage:
    python3 publish.py <input.json>            # validate + write files
    python3 publish.py <input.json> --check    # validate only

Input JSON (write it with json.dump, never by hand):
{
  "date": "YYYY-MM-DD",
  "id": "kebab-case-slug-YYYY-MM-DD",
  "typeNo": 1-6,
  "title": "...",
  "topics": "נושא · נושא · נושא",
  "readingTime": "כ-7 דקות קריאה",
  "body_md": "## פתיח...\\n\\n...",          # Markdown. '##' = section, '###' = sub-section.
                                              # Claim labels: [עובדה] [פרשנות] [ערכי] [פרשנות/ערכי]
  "dyk_md": "...",                           # 'Did you know' text, Markdown inline
  "dyk_source": "מקור: ...",
  "quiz": [ { "q": "...", "options": ["","","",""], "correct": 0-3,
              "explain": "one sentence", "topic": "short label" }, ... ],   # 3–5 items
  "sources": [ { "grade": "דרגה A — מקורות ראשוניים",
                 "items": ["Markdown line with a [link](https://...)", ...] }, ... ],
  "workNotes": ["internal notes — never shown on the page"]
}

Writes:
    pieces/<date>.json   the piece as the page renders it
    index.json           prepends {id,date,file,typeNo,type,title,topics,readingTime,quiz}
    md/<date>.md         a readable archive copy (title, tag, body, did-you-know, questions + answers, sources)
"""
import json
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:  # pragma: no cover
    sys.exit("missing dependency: pip install markdown (add --break-system-packages if needed)")

HERE = Path(__file__).resolve().parent
TYPES = {
    1: "השורשים של היום",
    2: "רגע מכריע",
    3: "דמות",
    4: "רעיון",
    5: "שתי פרשנויות",
    6: "היום בהיסטוריה",
}
CLAIMS = [("פרשנות/ערכי", "interp"), ("עובדה", "fact"), ("פרשנות", "interp"), ("ערכי", "value")]
FORBIDDEN_IN_BODY = ["לא מצאתי", "בהרצה זו", "בדקתי את", "לא הצלחתי לאמת", "TODO"]
HEB_LETTERS = ["א", "ב", "ג", "ד", "ה"]


def fail(msg):
    sys.exit(f"PUBLISH FAILED: {msg}")


def md_block(text):
    html = markdown.markdown(text, extensions=["extra", "sane_lists"])
    html = html.replace("<h3>", "<h4>").replace("</h3>", "</h4>")
    html = html.replace("<h2>", "<h3>").replace("</h2>", "</h3>")
    for label, cls in CLAIMS:
        html = html.replace(f"[{label}]", f'<span class="claim {cls}">{label}</span>')
    html = html.replace("<a href=", '<a target="_blank" rel="noopener" href=')
    return html.strip()


def md_inline(text):
    html = md_block(text)
    if html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
        html = html[3:-4]
    return html


def validate(p, index):
    req = ["date", "id", "typeNo", "title", "topics", "readingTime", "body_md", "dyk_md", "dyk_source", "quiz", "sources"]
    for k in req:
        if k not in p or p[k] in (None, "", []):
            fail(f"missing field '{k}'")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["date"]):
        fail("date must be YYYY-MM-DD")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", p["id"]):
        fail("id must be kebab-case ascii")
    if not p["id"].endswith(p["date"]):
        fail("id must end with the date")
    if p["typeNo"] not in TYPES:
        fail("typeNo must be 1-6")
    if any(e["date"] == p["date"] for e in index["pieces"]):
        fail(f"a piece for {p['date']} already exists — one piece per date")
    if any(e["id"] == p["id"] for e in index["pieces"]):
        fail("id already used")
    if len(re.findall(r"^## ", p["body_md"], flags=re.M)) < 3:
        fail("body_md needs at least 3 '## ' sections (opening, what happened, interpretation, today)")
    for bad in FORBIDDEN_IN_BODY:
        if bad in p["body_md"] or bad in p["dyk_md"]:
            fail(f"internal work note in reader-facing text: '{bad}' — move it to workNotes")
    words = len(re.findall(r"\S+", p["body_md"]))
    if not 700 <= words <= 2200:
        fail(f"body is {words} words; aim for a 5–8 minute read (~900–1,700 words)")
    q = p["quiz"]
    if not 3 <= len(q) <= 5:
        fail("quiz needs 3–5 questions")
    for i, item in enumerate(q, 1):
        if len(item.get("options", [])) != 4:
            fail(f"quiz {i}: exactly 4 options")
        if not isinstance(item.get("correct"), int) or not 0 <= item["correct"] <= 3:
            fail(f"quiz {i}: 'correct' must be an index 0-3")
        for k in ("q", "explain", "topic"):
            if not item.get(k):
                fail(f"quiz {i}: missing '{k}'")
    n_links = 0
    for g in p["sources"]:
        if not g.get("grade") or not g.get("items"):
            fail("each source group needs 'grade' and 'items'")
        n_links += sum(1 for it in g["items"] if re.search(r"\]\(https?://", it))
    if n_links < 4:
        fail("at least 4 linked sources are required")


def archive_md(p):
    lines = [f"# {p['title']}", "",
             f"**תגית:** {TYPES[p['typeNo']]} · **זמן קריאה:** {p['readingTime']} · **תאריך:** {p['date']}",
             f"**נושאים:** {p['topics']}", "", "---", "", p["body_md"].strip(), "", "---", "",
             "## הידעת?", "", p["dyk_md"].strip(), "", f"*{p['dyk_source']}*", "", "---", "",
             "## שאלות לבדיקה עצמית", ""]
    for i, item in enumerate(p["quiz"], 1):
        lines.append(f"**{i}. {item['q']}**")
        for j, opt in enumerate(item["options"]):
            lines.append(f"- {HEB_LETTERS[j]}. {opt}")
        lines.append("")
    lines += ["<details>", "<summary>תשובות</summary>", ""]
    for i, item in enumerate(p["quiz"], 1):
        lines.append(f"{i}. **{HEB_LETTERS[item['correct']]}** — {item['explain']}")
    lines += ["", "</details>", "", "---", "", "## מקורות", ""]
    for g in p["sources"]:
        lines.append(f"**{g['grade']}**")
        lines += [f"- {it}" for it in g["items"]]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    if len(sys.argv) < 2:
        fail(__doc__)
    p = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    index_path = HERE / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"pieces": []}
    validate(p, index)
    if "--check" in sys.argv:
        print("OK (check only)")
        return

    t = TYPES[p["typeNo"]]
    piece = {
        "id": p["id"], "date": p["date"], "typeNo": p["typeNo"], "type": t,
        "title": p["title"], "topics": p["topics"], "readingTime": p["readingTime"],
        "dyk": {"html": md_inline(p["dyk_md"]), "source": p["dyk_source"]},
        "body": md_block(p["body_md"]),
        "sources": [{"grade": g["grade"], "items": [md_inline(it) for it in g["items"]]} for g in p["sources"]],
        "workNotes": p.get("workNotes", []),
    }
    entry = {
        "id": p["id"], "date": p["date"], "file": f"pieces/{p['date']}.json",
        "typeNo": p["typeNo"], "type": t, "title": p["title"], "topics": p["topics"],
        "readingTime": p["readingTime"], "quiz": p["quiz"],
    }
    (HERE / "pieces").mkdir(exist_ok=True)
    (HERE / "md").mkdir(exist_ok=True)
    (HERE / "pieces" / f"{p['date']}.json").write_text(json.dumps(piece, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "md" / f"{p['date']}.md").write_text(archive_md(p), encoding="utf-8")
    index["pieces"] = sorted([entry] + index["pieces"], key=lambda e: e["date"], reverse=True)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    nxt = p["typeNo"] % 6 + 1
    print(f"OK published {p['date']} · {t} · {p['title']}")
    print(f"next type in rotation: {nxt} — {TYPES[nxt]}")


if __name__ == "__main__":
    main()
