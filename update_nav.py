"""Refresh NAV, NAV date and 1-year return in index.html's live-data block.

Sources (both free, no login):
  - AMFI official daily NAV file: https://www.amfiindia.com/spages/NAVAll.txt
  - mfapi.in NAV history (for the 1-year return): https://api.mfapi.in/mf/<code>

Cost (expense ratio) and AUM are NOT changed here - edit them by hand in
index.html if they move. Runs from GitHub Actions; can also be run locally:
    python scripts/update_nav.py
"""
import datetime as dt
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
MFAPI_URL = "https://api.mfapi.in/mf/{code}"
BLOCK = re.compile(r'(<script type="application/json" id="live-data">)(.*?)(</script>)', re.S)

# Words that must all appear in the AMFI scheme name (after normalising).
# A fund can also be pinned by adding "amfi": <scheme code> to its entry in index.html.
MATCH = {
    "kotak_mom50": [["kotak"], ["midcap"], ["momentum 50"]],
    "tata_mom50":  [["tata"], ["midcap"], ["momentum 50"]],
    "edel_mom50":  [["edelweiss"], ["midcap"], ["momentum 50"]],
    "nippon_v20":  [["nippon"], ["value 20"], ["index"]],
    "axis_v50":    [["axis"], ["value 50"], ["index"]],
    "uti_v50":     [["uti "], ["value 50"], ["index"]],
    "icici_v30":   [["icici"], ["value 30"], ["index"]],
    "mirae_sc250": [["mirae"], ["smallcap", "small cap"], ["quality"], ["fof", "fund of fund"]],
    "groww_sc250": [["groww"], ["smallcap", "small cap"], ["quality"]],
    "uti_ms400":   [["uti "], ["400"], ["momentum quality", "momentum and quality"]],
    "icici_v20":   [["icici"], ["value 20"], ["index"]],
}
BAD = ("idcw", "dividend", "regular", "payout", "bonus", "segregated")


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 godmf-refresh"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"  fetch failed ({i + 1}/{tries}) {url}: {e}")
            time.sleep(5)
    return None


def norm(s):
    s = s.lower().replace("&", " and ")
    return " " + re.sub(r"[^a-z0-9]+", " ", s).strip() + " "


def parse_amfi(text):
    """Return {code: (name, nav, date_iso)} for every scheme line."""
    out = {}
    for line in text.splitlines():
        p = line.split(";")
        if len(p) != 6 or not p[0].strip().isdigit():
            continue
        try:
            nav = float(p[4])
            d = dt.datetime.strptime(p[5].strip(), "%d-%b-%Y").date().isoformat()
        except ValueError:
            continue
        out[p[0].strip()] = (p[3].strip(), nav, d)
    return out


def find_code(fid, amfi):
    rules = MATCH.get(fid)
    if not rules:
        return None
    hits = []
    for code, (name, _, _) in amfi.items():
        n = norm(name)
        if " direct " not in n or " growth " not in n or any(b in n for b in BAD):
            continue
        if all(any(alt in n for alt in group) for group in rules):
            hits.append((len(name), code, name))
    if not hits:
        return None
    hits.sort()
    if len(hits) > 1:
        print(f"  {fid}: several matches, using shortest name: {[h[2] for h in hits]}")
    return hits[0][1]


def one_year_return(code, nav_now, date_now):
    txt = get(MFAPI_URL.format(code=code))
    if not txt:
        return None
    try:
        rows = json.loads(txt)["data"]  # newest first, date "DD-MM-YYYY"
    except (ValueError, KeyError):
        return None
    target = dt.date.fromisoformat(date_now) - dt.timedelta(days=365)
    for r in rows:
        d = dt.datetime.strptime(r["date"], "%d-%m-%Y").date()
        if d <= target:
            if (target - d).days > 7:
                return None  # gap too big - fund probably younger than a year
            old = float(r["nav"])
            return round((nav_now / old - 1) * 100, 2) if old > 0 else None
    return None


def main():
    html = PAGE.read_text(encoding="utf-8")
    m = BLOCK.search(html)
    if not m:
        sys.exit("live-data block not found in index.html")
    data = json.loads(m.group(2))
    funds = data["funds"]

    text = get(AMFI_URL)
    if not text:
        sys.exit("Could not download AMFI NAV file")
    amfi = parse_amfi(text)
    print(f"AMFI file: {len(amfi)} schemes")

    ok, failed = [], []
    for fid, f in funds.items():
        code = str(f.get("amfi") or find_code(fid, amfi) or "")
        if code not in amfi:
            print(f"- {fid}: no AMFI match")
            failed.append(fid)
            continue
        name, nav, nav_date = amfi[code]
        print(f"- {fid}: {code} {name} -> NAV {nav} on {nav_date}")
        prev = f.get("nav") or nav
        if abs(nav / prev - 1) > 0.15 or nav_date < f.get("navDate", ""):
            print(f"  skipped: implausible vs stored NAV {prev} / {f.get('navDate')}")
            failed.append(fid)
            continue
        f["nav"], f["navDate"] = round(nav, 4), nav_date
        r1 = one_year_return(code, nav, nav_date)
        if r1 is not None:
            f["r1"] = r1
        ok.append(fid)

    ist_today = (dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)).date().isoformat()
    if ok:
        data["updated"] = ist_today
    new_html = html[: m.start(2)] + json.dumps(data, ensure_ascii=False) + html[m.end(2):]
    PAGE.write_text(new_html, encoding="utf-8")
    print(f"\nUpdated {len(ok)}/{len(funds)} funds. Failed: {failed or 'none'}")
    if len(failed) > len(funds) / 2:
        sys.exit("More than half the funds failed - check the log above")


if __name__ == "__main__":
    main()
