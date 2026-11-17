"""Parse scores/alerts/confidence from the AI analysts' markdown reports (or <panel>.scores.json if present)."""
import re, json, datetime as dt
from .common import REPORTS

MINUS = str.maketrans({"−": "-", "–": "-", "＋": "+"})
COLOR = {"红": "红", "黄": "黄", "绿": "绿", "🔴": "红", "🟡": "黄", "🟢": "绿"}

def _color(s):
    for k, v in COLOR.items():
        if k in s:
            return v
    return None

def _int(s):
    m = re.match(r"^\s*\**\s*([+-]?[0-2])\s*\**\s*$", s.translate(MINUS))
    return int(m.group(1)) if m else None

def parse(text, tickers):
    out = {}
    # 1) markdown tables with a 评分 column
    lines = text.splitlines()
    hdr = None
    for ln in lines:
        if ln.strip().startswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if any("评分" in c for c in cells) and cells and ("标的" in cells[0] or cells[0] == ""):
                hdr = cells; continue
            if hdr and cells:
                t = re.match(r"([A-Z]{1,5})", cells[0].replace("*", ""))
                if t and t.group(1) in tickers and t.group(1) not in out:
                    rec = {}
                    for i, h in enumerate(hdr):
                        if i >= len(cells): break
                        if "评分" in h and "score" not in rec: rec["score"] = _int(cells[i])
                        elif "警报" in h: rec["alert"] = _color(cells[i])
                        elif "置信" in h: rec["confidence"] = cells[i][:1]
                    if rec.get("score") is not None:
                        out[t.group(1)] = rec
        else:
            hdr = None if not ln.strip() else hdr
    # 2) per-ticker sections: "标的：XXX" / "## XXX" / "### n. XXX"
    pos = []
    for m in re.finditer(r"(?m)^(?:\**\s*)?(?:#+\s*(?:\d+\.\s*)?|[-*\s]*\**标的[：:]\s*\**\s*)([A-Z]{1,5})\b", text):
        if m.group(1) in tickers:
            pos.append((m.start(), m.group(1)))
    for j, (p, t) in enumerate(pos):
        if t in out:
            continue
        blk = text[p: pos[j + 1][0] if j + 1 < len(pos) else len(text)]
        ms = re.search(r"评分\**\s*[：:]\s*\**\s*([+\-−–]?\s*[0-2])", blk)
        if not ms:
            continue
        rec = {"score": int(ms.group(1).translate(MINUS).replace(" ", ""))}
        ma = re.search(r"警报级别\**\s*[：:]\s*\**([^\n]{0,12})", blk)
        if ma: rec["alert"] = _color(ma.group(1))
        mc = re.search(r"置信度\**\s*[：:]\s*\**\s*([高中低])", blk)
        if mc: rec["confidence"] = mc.group(1)
        out[t] = rec
    return out

def latest(panel, run_date, tickers):
    """Return (date, {ticker: rec}) from the newest report <= run_date."""
    dirs = sorted([d for d in REPORTS.iterdir() if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}$", d.name)
                   and d.name <= str(run_date)], reverse=True) if REPORTS.exists() else []
    for d in dirs:
        js, md = d / f"{panel}.scores.json", d / f"{panel}.md"
        try:
            if js.exists():
                return dt.date.fromisoformat(d.name), json.loads(js.read_text())
            if md.exists():
                rec = parse(md.read_text(encoding="utf-8"), tickers)
                if rec:
                    return dt.date.fromisoformat(d.name), rec
        except Exception:
            continue
    return None, {}
