import json, os, pathlib, urllib.request, sys, ssl
from datetime import datetime, timezone, timedelta

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# Read from env (GitHub Actions) or config.json (local)
APP_TOKEN = os.environ.get("WXPUSHER_TOKEN")
UID = os.environ.get("WXPUSHER_UID")
if not APP_TOKEN or not UID:
    cfg_path = pathlib.Path(__file__).parent / "config.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
        APP_TOKEN = APP_TOKEN or cfg.get("appToken", "")
        UID = UID or cfg.get("uid", "")
    if not APP_TOKEN or not UID:
        print("ERROR: Set WXPUSHER_TOKEN/WXPUSHER_UID env vars or config.json")
        sys.exit(1)

MODE = sys.argv[1] if len(sys.argv) > 1 else "selected"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 aihot-skill/0.3.0"
BJ = timezone(timedelta(hours=8))
now_bj = datetime.now(BJ)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))

def he(s):
    if not s: return ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def ss(val, fb=""):
    if val is None or val == "": return fb
    return str(val)

def item_html(item):
    t = he(ss(item.get("title"), item.get("title_en", "")))
    src = he(ss(item.get("source"), ""))
    link = he(ss(item.get("url"), item.get("sourceUrl", "")))
    sm = he(ss(item.get("summary"), ""))
    h = "<li><b>" + t + "</b>"
    if src: h += " - " + src
    if sm: h += "<br>" + sm
    if link: h += '<br><a href="' + link + '">' + link + '</a>'
    h += "</li>\n"
    return h

def push(content, summary):
    p = {"appToken": APP_TOKEN, "content": content, "contentType": 2, "uids": [UID], "summary": summary}
    d = json.dumps(p, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request("https://wxpusher.zjiecode.com/api/send/message",
        data=d, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as r:
        return json.loads(r.read().decode("utf-8"))

def build_html(title, groups, footer):
    html = "<h3>" + title + "</h3>\n"
    for sec_name, items in groups:
        if sec_name:
            html += "<p><b>" + he(sec_name) + "</b></p>\n"
        html += "<ul>\n"
        for item in items:
            html += item_html(item)
        html += "</ul>\n"
    html += footer
    return html

# ===== Main =====
if MODE == "daily":
    print("Fetching daily...")
    resp = fetch("https://aihot.virxact.com/api/public/daily")
    daily = resp.get("daily", resp)
    date = ss(daily.get("date"), now_bj.strftime("%Y-%m-%d"))
    title = "AI HOT Daily - " + date
    sections = daily.get("sections") or daily.get("categories") or []
    groups = []
    for sec in sections:
        name = ss(sec.get("name"), sec.get("category", ""))
        entries = sec.get("items") or sec.get("entries") or []
        groups.append((name, entries))
    summary = "AI HOT Daily"
else:
    print("Fetching selected...")
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp = fetch("https://aihot.virxact.com/api/public/items?mode=selected&since=" + since + "&take=30")
    items = resp.get("items", [])
    title = "AI HOT - " + now_bj.strftime("%m/%d %H:%M")
    cat_labels = {"ai-models": "Model Release", "ai-products": "Product Launch",
                  "industry": "Industry News", "paper": "AI Papers", "tip": "Tips & Views"}
    buckets = {}
    for item in items:
        cat = ss(item.get("category"), "Other")
        buckets.setdefault(cat, []).append(item)
    groups = [(cat_labels.get(c, c), items) for c, items in buckets.items()]
    summary = "AI HOT"

content = build_html(title, groups, "<p>aihot.virxact.com</p>")
if not content:
    content = "<h3>" + title + "</h3>\n<p><i>no content</i></p>\n<p>aihot.virxact.com</p>"

print("Content: " + str(len(content)) + " chars")
r = push(content, summary)
print("code=" + str(r.get("code")) + " msg=" + str(r.get("msg")))
if r.get("code") == 1000:
    print("OK!")
else:
    print("FAIL: " + str(r))
    sys.exit(1)