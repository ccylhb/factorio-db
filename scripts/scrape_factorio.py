# -*- coding: utf-8 -*-
"""Factorio scraper — wiki.factorio.com (official wiki).

Data lives on Infobox:<Title> subpages transcluded via {{:Infobox:X}}.
Two-phase fetch: item pages (intro) + infobox pages (params).
Recipe strings look like: "Time, 3.2 + Iron ore, 1".
"""
import json, os, re, sys, time, urllib.request, urllib.parse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "src", "data")
CACHE_DIR = os.path.join(BASE_DIR, "scripts", "cache")
API = "https://wiki.factorio.com/api.php"
UA = "FactorioDB/1.0 (site: factorio-db.pages.dev; contact franceiwhdbks865@gmail.com)"

FETCH_CATS = ["Intermediate products", "Combat", "Logistics", "Production"]

num_re = re.compile(r"-?\d+(?:\.\d+)?")


def num(v):
    if v is None:
        return None
    m = num_re.search(v)
    return float(m.group(0)) if m else None


def strip_comments(wt):
    return re.sub(r"<!--.*?-->", "", wt, flags=re.S)


def opener_proxy():
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({"https": "http://127.0.0.1:7897",
                                     "http": "http://127.0.0.1:7897"}))


OP = urllib.request.build_opener()
USE_PROXY = [False]


def api(p, retry=True):
    url = API + "?" + urllib.parse.urlencode({**p, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        return json.load(OP.open(req, timeout=40))
    except Exception as e:
        if retry and not USE_PROXY[0]:
            print("  [net] direct failed, switching to proxy:", str(e)[:50])
            OP_ = opener_proxy()
            globals()["OP"] = OP_
            USE_PROXY[0] = True
            return api(p, retry=False)
        if retry:
            time.sleep(3)
            return api(p, retry=False)
        raise


def split_params(body):
    parts, buf = [], []
    depth_t = depth_l = 0
    i = 0
    while i < len(body):
        c = body[i]
        if c == "|" and depth_t == 0 and depth_l == 0:
            parts.append("".join(buf)); buf = []
        else:
            buf.append(c)
            if body.startswith("{{", i): depth_t += 1; i += 1
            elif body.startswith("}}", i): depth_t -= 1; i += 1
            elif body.startswith("[[", i): depth_l += 1; i += 1
            elif body.startswith("]]", i): depth_l -= 1; i += 1
        i += 1
    parts.append("".join(buf))
    return parts


def parse_params(body):
    out = {}
    for part in split_params(body):
        part = part.strip()
        if part.startswith("|"):
            part = part[1:]
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip().lower()
        if not k or k in out:
            continue
        out[k] = v.strip()
    return out


def clean(v):
    if not v:
        return ""
    v = strip_comments(v)
    v = re.sub(r"<br\s*/?>", "; ", v)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)
    v = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", v)
    v = v.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", v).strip()


def first_para(wt):
    body = strip_comments(wt)
    m = re.search(r"\}\}", body)
    if m:
        body = body[m.end():]
    for ln in body.splitlines():
        ln = ln.strip()
        if ln and not ln.startswith(("=", "{", "|", "[[", "<", "#", "'")):
            return clean(ln)[:400]
    return ""


def parse_recipe(v):
    """'Time, 3.2 + Iron ore, 1' -> {time, ingredients:[{name,qty}]}"""
    if not v:
        return {"time": None, "ingredients": []}
    time_v = None
    ingredients = []
    for chunk in v.split("+"):
        bits = chunk.split(",")
        if len(bits) < 2:
            continue
        name = bits[0].strip()
        qty = num(",".join(bits[1:]).strip())
        if name.lower() == "time":
            time_v = qty
        else:
            ingredients.append({"name": name, "qty": qty})
    return {"time": time_v, "ingredients": ingredients}


def cat_members(cat):
    titles, cont = [], {}
    while True:
        r = api({"action": "query", "list": "categorymembers", "cmtitle": "Category:" + cat,
                 "cmtype": "page", "cmnamespace": "0", "cmlimit": "500", **cont})
        titles += [m["title"] for m in r.get("query", {}).get("categorymembers", [])]
        cont = r.get("continue") or {}
        if not cont:
            return titles
        time.sleep(0.4)


def fetch_wikitexts(titles, cache_path):
    wts = {}
    if os.path.exists(cache_path):
        wts = json.load(open(cache_path, encoding="utf-8"))
    titles = [t for t in titles if t not in wts]
    if not titles:
        return wts
    batch = 15
    for i in range(0, len(titles), batch):
        chunk = titles[i:i + batch]
        r = None
        for attempt in range(3):
            try:
                r = api({"action": "query", "prop": "revisions", "rvprop": "content",
                         "rvslots": "main", "redirects": 1, "titles": "|".join(chunk)})
                break
            except Exception as e:
                print(f"  [batch {i}] ERR {str(e)[:50]}, retry {attempt + 1}")
                time.sleep(3)
        if not r:
            continue
        for pg in r.get("query", {}).get("pages", {}).values():
            rev = pg.get("revisions") or []
            wts[pg["title"]] = rev[0]["slots"]["main"]["*"] if rev else ""
        if (i // batch) % 10 == 0:
            print(f"  fetched {min(i + batch, len(titles))}/{len(titles)}")
        time.sleep(0.3)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    json.dump(wts, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
    return wts


def extract_infobox(wt):
    """Parse {{Infobox|...}} from an Infobox: page."""
    if not wt:
        return None
    m = re.search(r"\{\{\s*Infobox\s*\|", wt, flags=re.I)
    if not m:
        return None
    start = m.start() + 2
    depth, i = 1, start
    while i < len(wt) - 1 and depth > 0:
        if wt[i] == "{":
            depth += 1
        elif wt[i] == "}":
            depth -= 1
        i += 1
    body = wt[start:i - 1]
    return parse_params(body)


def slug(t):
    s = re.sub(r"\s+", "-", t.strip().lower())
    return re.sub(r"[^a-z0-9\-]", "", s) or "item"


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    titles = []
    for c in FETCH_CATS:
        got = cat_members(c)
        print(f"[cat] {c}: {len(got)}")
        titles.extend(got)
        time.sleep(0.3)
    titles = sorted(set(t for t in titles if not t.startswith("Category:")))
    print(f"[total] {len(titles)} unique pages")

    page_cache = os.path.join(CACHE_DIR, "pages.json")
    ibox_cache = os.path.join(CACHE_DIR, "infoboxes.json")
    wts = fetch_wikitexts(titles, page_cache)
    ibox_titles = ["Infobox:" + t for t in titles]
    ibox_wts = fetch_wikitexts(ibox_titles, ibox_cache)

    out = []
    seen = set()
    for t in titles:
        key = slug(t)
        if key in seen:
            continue
        seen.add(key)
        ibox = extract_infobox(ibox_wts.get("Infobox:" + t, ""))
        if not ibox:
            continue
        p = ibox
        recipe = parse_recipe(p.get("recipe", ""))
        rec = {
            "title": t,
            "slug": key,
            "internal_name": p.get("internal-name", ""),
            "category": clean(p.get("category", "")),
            "stack_size": num(p.get("stack-size")),
            "producers": clean(p.get("producers", "")),
            "time": recipe["time"],
            "ingredients": recipe["ingredients"],
            "intro": first_para(wts.get(t, "")),
            "image": clean(p.get("image", "")),
            # frontend (items/[slug].astro 等) 依赖 icon_file；图标文件预置于 public/icons/
            "icon_file": re.sub(r"[\s()]", "_", t) + ".png",
        }
        out.append(rec)
    path = os.path.join(DATA_DIR, "factorio_items.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[out] items: {len(out)}")
    withr = [x for x in out if x["time"]]
    print(f"[out] with recipe: {len(withr)}")


if __name__ == "__main__":
    main()
