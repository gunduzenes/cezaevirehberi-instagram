"""
GitHub Actions üzerinde çalışan Instagram yayınlayıcı (Instagram API, Instagram Login).

  python3 instagram/publish.py post|story

Ortam değişkenleri:
  IG_TOKEN   Instagram kullanıcı erişim anahtarı (GitHub secret)
  RAW_BASE   https://raw.githubusercontent.com/<owner>/<repo>/<sha>   (görsellerin herkese açık adresi)
  DRY_RUN=1  Paylaşmadan yalnızca görselleri üretir

Akış: content.json -> ig_render.py ile görseller -> instagram/out/ altına yazılır ->
iş akışı bunları commit edip push eder -> bu betik ikinci aşamada (--publish) Instagram'a gönderir.
"""
import json, os, sys, time, pathlib, datetime, urllib.request, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
IG = ROOT / "instagram"
sys.path.insert(0, str(IG))
import ig_render  # noqa: E402

API = "https://graph.instagram.com/v21.0"
TODAY = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).date().isoformat()


def call(method, path, **params):
    params["access_token"] = os.environ["IG_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
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


def content_path():
    for p in (ROOT / "content.json", ROOT / "content" / "content.json"):
        if p.exists():
            return p
    raise SystemExit("content.json bulunamadı")


def prepare(mode):
    state_p = IG / "durum.json"
    state = json.loads(state_p.read_text())
    key = "post" if mode == "post" else "story"
    if any(x.get("date") == TODAY and key in x for x in state.get("log", [])):
        print("Bugün zaten paylaşılmış:", key)
        return None
    content = json.loads(content_path().read_text())
    out = IG / "out" / f"{TODAY}-{mode}"
    plan = ig_render.make_post(content, state, out) if mode == "post" else ig_render.make_story(content, state, out)
    # Promo görselini de out klasörüne kopyala ki tek yerden yayınlansın
    imgs = []
    for p in plan["images"]:
        p = pathlib.Path(p)
        if p.parent != out:
            out.mkdir(parents=True, exist_ok=True)
            dst = out / p.name; dst.write_bytes(p.read_bytes()); p = dst
        imgs.append(str(p.relative_to(ROOT)))
    plan["images"] = imgs
    (out / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(json.dumps(plan, ensure_ascii=False, indent=1))
    return out / "plan.json"


def publish(plan_path):
    plan = json.loads(pathlib.Path(plan_path).read_text())
    base = os.environ["RAW_BASE"].rstrip("/")
    urls = [f"{base}/{urllib.parse.quote(p)}" for p in plan["images"]]
    me = call("GET", "me", fields="user_id,username")
    if me.get("username") != "cezaevirehberi":
        raise SystemExit(f"Beklenmeyen hesap: {me.get('username')}")
    uid = me["user_id"]
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
    res = call("POST", f"{uid}/media_publish", creation_id=cid)
    print("Yayınlandı:", res)
    ig_render.commit(str(IG / "durum.json"), str(plan_path))


if __name__ == "__main__":
    if sys.argv[1] == "--publish":
        publish(sys.argv[2])
    else:
        p = prepare(sys.argv[1])
        gh_out = os.environ.get("GITHUB_OUTPUT")
        if gh_out:
            with open(gh_out, "a") as f:
                f.write(f"plan={p.relative_to(ROOT) if p else ''}\n")
