#!/usr/bin/env python3
"""BNM（マレーシア中央銀行）の公表為替レートを取得して rates.json を更新する。

- 一次情報のみ。取得できなかった項目は推測で埋めず、前回値を維持して stale=true を立てる。
- BNMは営業日のみ公表。土日祝は前営業日の値が返る（rate.date で判別できる）。
"""
import json
import os
import sys
import ssl
import urllib.request
from datetime import datetime, timezone

API = "https://api.bnm.gov.my/public/exchange-rate?session=1130&quote=rm"
HEADERS = {"Accept": "application/vnd.BNM.API.v1+json"}
OUT = os.path.join(os.path.dirname(__file__), "..", "rates.json")
KEEP_HISTORY = 400


def _ssl_context():
    """一部の環境（企業プロキシ等）でシステムの証明書チェーンが信頼できないため、
    certifi があればそちらを使う。GitHub Actions 上ではどちらでも通る。"""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch():
    req = urllib.request.Request(API, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as r:
        return json.loads(r.read())


def middle(rate):
    """BNMは buying / selling を返す。middle_rate が null のことがあるので自前で中値を出す。"""
    if rate.get("middle_rate") is not None:
        return rate["middle_rate"]
    b, s = rate.get("buying_rate"), rate.get("selling_rate")
    if b is None or s is None:
        return None
    return (b + s) / 2


def load_prev():
    try:
        with open(OUT, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"history": []}


def main():
    prev = load_prev()
    try:
        data = fetch()
    except Exception as e:
        # 取得失敗。前回値を維持して stale を立てる（値を推測しない）
        prev["stale"] = True
        prev["last_error"] = f"{type(e).__name__}: {e}"
        prev["last_attempt_utc"] = datetime.now(timezone.utc).isoformat()
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(prev, f, ensure_ascii=False, indent=2)
        print("fetch failed, kept previous values:", e, file=sys.stderr)
        return 0

    rows = {r["currency_code"]: r for r in data.get("data", [])}
    jpy, usd = rows.get("JPY"), rows.get("USD")
    if not jpy:
        prev["stale"] = True
        prev["last_error"] = "JPY not in BNM response"
        prev["last_attempt_utc"] = datetime.now(timezone.utc).isoformat()
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(prev, f, ensure_ascii=False, indent=2)
        print("JPY missing, kept previous values", file=sys.stderr)
        return 0

    # JPYは unit=100（RM per 100 JPY）。RM1あたりの円に直す
    jpy_mid = middle(jpy["rate"])
    unit = jpy.get("unit", 100)
    rm_to_jpy = unit / jpy_mid

    out = {
        "source": "Bank Negara Malaysia (BNM) Open API",
        "source_url": "https://api.bnm.gov.my/public/exchange-rate?session=1130&quote=rm",
        "session": "1130",
        "rate_date": jpy["rate"]["date"],
        "bnm_last_updated": data.get("meta", {}).get("last_updated"),
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "stale": False,
        "myr_to_jpy": round(rm_to_jpy, 4),
        "jpy_per_100_myr": round(rm_to_jpy * 100, 2),
        "raw": {
            "JPY": {"unit": unit, "buying": jpy["rate"]["buying_rate"], "selling": jpy["rate"]["selling_rate"]},
        },
        "note": "中値（buying と selling の平均）で換算した参考値。実際の送金では銀行手数料とスプレッドが乗る。",
    }
    if usd:
        usd_mid = middle(usd["rate"])
        out["usd_to_myr"] = round(usd_mid, 4)
        out["raw"]["USD"] = {"unit": usd.get("unit", 1), "buying": usd["rate"]["buying_rate"], "selling": usd["rate"]["selling_rate"]}
        out["usd_to_jpy"] = round(usd_mid * rm_to_jpy, 2)

    history = prev.get("history", [])
    entry = {"date": out["rate_date"], "myr_to_jpy": out["myr_to_jpy"], "usd_to_myr": out.get("usd_to_myr")}
    if not history or history[-1]["date"] != entry["date"]:
        history.append(entry)
    else:
        history[-1] = entry
    out["history"] = history[-KEEP_HISTORY:]

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"RM1 = {out['myr_to_jpy']} JPY  (BNM {out['rate_date']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
