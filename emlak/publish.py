"""
Emlak Rehberi (@emlakrehberiapp) Instagram yayınlayıcı — GitHub Actions'ta çalışır.

  python3 emlak/publish.py post            -> görselleri hazırlar (emlak/out/<tarih>-post)
  python3 emlak/publish.py --publish PLAN  -> Instagram'a gönderir, durum.json'u günceller

Ortam: IG_TOKEN (Instagram erişim anahtarı), RAW_BASE (görsellerin herkese açık adresi).
"""
import json, os, sys, time, pathlib, datetime, urllib.request, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "emlak"
sys.path.insert(0, str(D))
import ig_render  # noqa: E402

USERNAME = "emlakrehberiapp"
API = "https://graph.instagram.com/v21.0"
TODAY = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).date().isoformat()


def call(method, path, **params):
    params["access_token"] = os.environ["IG_TOKEN"].strip().strip("\"'")
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    req = urllib.request.Request(url + "?" + data.decode()) if method == "GET" else urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Instagram API hatası {e.code}: {e.read().decode()[:500]}")


def wait_ready(cid):
    for _ in range(30):
        st = call("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise SystemExit(f"Medya işlenemedi: {cid} {st}")
        time.sleep(5)
    raise SystemExit("Medya hazırlanması zaman aşımına uğradı")


def prepare(mode):
    state_p = D / "durum.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {}
    if any(x.get("date") == TODAY and mode in x for x in state.get("log", [])):
        print("Bugün zaten paylaşılmış:", mode)
        return None
    content = json.loads((ROOT / "emlak-content.json").read_text())
    out = D / "out" / f"{TODAY}-{mode}"
    plan = ig_render.make_post(content, state, out) if mode == "post" else ig_render.make_story(content, state, out)
    plan["images"] = [str(pathlib.Path(p).relative_to(ROOT)) for p in plan["images"]]
    (out / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(json.dumps(plan, ensure_ascii=False, indent=1))
    return out / "plan.json"


def publish(plan_path):
    plan = json.loads(pathlib.Path(plan_path).read_text())
    base = os.environ["RAW_BASE"].rstrip("/")
    urls = [f"{base}/{urllib.parse.quote(p)}" for p in plan["images"]]
    me = call("GET", "me", fields="user_id,username")
    if me.get("username") != USERNAME:
        raise SystemExit(f"Beklenmeyen hesap: {me.get('username')}")
    uid = me.get("user_id") or me["id"]
    if plan["type"] == "story":
        cid = call("POST", f"{uid}/media", image_url=urls[0], media_type="STORIES")["id"]
    elif len(urls) == 1:
        cid = call("POST", f"{uid}/media", image_url=urls[0], caption=plan["caption"])["id"]
    else:
        kids = []
        for u in urls:
            k = call("POST", f"{uid}/media", image_url=u, is_carousel_item="true")["id"]
            wait_ready(k); kids.append(k)
        cid = call("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=plan["caption"])["id"]
    wait_ready(cid)
    print("Yayınlandı:", call("POST", f"{uid}/media_publish", creation_id=cid))
    ig_render.commit(str(D / "durum.json"), str(plan_path))


if __name__ == "__main__":
    if sys.argv[1] == "--publish":
        publish(sys.argv[2])
    else:
        p = prepare(sys.argv[1])
        gh_out = os.environ.get("GITHUB_OUTPUT")
        if gh_out:
            with open(gh_out, "a") as f:
                f.write(f"plan={p.relative_to(ROOT) if p else ''}\n")
