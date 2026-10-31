"""
Cezaevi Rehberi Instagram görsel üretici.

Kullanım:
  python3 ig_render.py post   <content.json> <durum.json> <cikti_klasoru>
  python3 ig_render.py story  <content.json> <durum.json> <cikti_klasoru>

- Metinler content.json'dan BİREBİR alınır; hiçbir metin uydurulmaz.
- Örnek ceza / yatar süre / oran içeren konu paylaşılmaz (İnfaz Süreci ve
  hukuki süreç konuları ile Pro konular hariç tutulur).
- "Av. Enes Gündüz" adı hiçbir görselde veya açıklamada geçmez.
- Sonuç: cikti_klasoru/plan.json (görsel yolları + açıklama metni).
  Paylaşım BAŞARILI olduktan sonra: python3 ig_render.py commit <durum.json> <cikti_klasoru>/plan.json
"""
import json, sys, re, html, pathlib, datetime

HERE = pathlib.Path(__file__).resolve().parent
ALLOWED_TOPICS = [
    "ilk-adimlar", "telefon-evrak", "para-yatirma-atm", "ziyaret-hazirlik", "acik-kapali-gorus",
    "tutuklu-hukumlu-farki", "telefon-kurallar", "kantin", "ziyaret-kimler", "e-gorus",
    "esya-teslim", "mektup-esya", "esya-cikisi", "saglik", "aile-olaylari", "tahliye",
    "sikayet-yollari", "avukat-gorusu", "egitim", "oy", "yabanci",
]
PROMOS = ["promo-tanitim.jpg", "promo-infaz.jpg"]
PROMO_CAPTIONS = {
    "promo-tanitim.jpg": "Yakınınız cezaevinde mi?\nTelefon görüşmesi için gereken belgeler, VakıfBank ATM'den para yatırma, ziyaret kuralları ve infaz süreci… Hepsi adım adım, tek uygulamada.\n\nCezaevi Rehberi App Store'da ücretsiz. Bağlantı profilde.",
    "promo-infaz.jpg": "İnfaz hesabını Cezaevi Rehberi uygulamasında yapabilirsiniz: koşullu salıverilme, denetimli serbestlik, açık cezaevine ayrılma ve cezaevinde kalınacak süre.\n\nSonuç her dosyanın kendi bilgilerine göre değişir; kesin bilgi için avukatınıza danışın.\n\nUygulama App Store'da ücretsiz. Bağlantı profilde.",
}
DISCLAIMER = "Bilgilendirme amaçlıdır, hukuki tavsiye değildir."
TAGS = "#cezaevi #cezaevirehberi #tutuklu #hükümlü #cezaevigörüşü #istanbul"

NAVY, PAPER, INK, INKSOFT, LINE, GOLD_D, GOLD_L, MUTED = "#1C3049", "#F6F4EF", "#1E3550", "#4A5D74", "#E4DFD5", "#D5B57B", "#A9834A", "#B7C3D2"
SERIF, SANS = "Lora, Georgia, serif", "Inter, system-ui, sans-serif"
LOGO = ('<svg width="{s}" height="{s}" viewBox="0 0 100 100"><path d="M34 75V38a16.5 16.5 0 0 1 33 0v37" fill="none" stroke="{c}" stroke-width="3.2"/>'
        '<path d="M26 75h49" stroke="{c}" stroke-width="3.2"/><circle cx="50.5" cy="47.5" r="5.5" fill="{c}"/><path d="M46.6 51.7L47.7 62.5H52.3L53.4 51.7Z" fill="{c}"/></svg>')


def e(t):
    return html.escape(t, quote=False)


def load(p, default):
    p = pathlib.Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def topics(content):
    out = {}
    for c in content["categories"]:
        for t in c["topics"]:
            out[t["id"]] = (c["title"], t)
    for x in content.get("extraTopics", []):
        out[x["topic"]["id"]] = (x["categoryId"], x["topic"])
    return out


def section_items(s):
    """Bölümü (tür, metin) parçalarına ayırır; metinler birebir."""
    items = []
    if s.get("body"):
        items.append(("body", s["body"]))
    for b in s.get("bullets", []):
        items.append(("bullet", b))
    for i, st in enumerate(s.get("steps", []), 1):
        items.append((f"step{i}", st))
    if s.get("tip"):
        items.append(("tip", s["tip"]))
    if s.get("warning"):
        items.append(("warning", s["warning"]))
    return items


def chunk(items, budget=680):
    pages, cur, n = [], [], 0
    for it in items:
        L = len(it[1]) + 60
        if cur and n + L > budget:
            pages.append(cur); cur, n = [], 0
        cur.append(it); n += L
    if cur:
        pages.append(cur)
    return pages


def frame(inner, bg, fg, w=1080, h=1350, pad="96px 96px 80px"):
    return (f"<!doctype html><html lang='tr'><head><meta charset='utf-8'><style>body{{margin:0}}</style></head><body>"
            f"<div style=\"width:{w}px;height:{h}px;box-sizing:border-box;padding:{pad};background:{bg};color:{fg};font-family:{SANS};display:flex;flex-direction:column;justify-content:space-between\">{inner}</div></body></html>")


def footer(light, right):
    col = INKSOFT if light else MUTED
    border = LINE if light else "rgba(246,244,239,0.18)"
    return (f"<div style='display:flex;align-items:center;justify-content:space-between;border-top:2px solid {border};padding-top:36px'>"
            f"<span style='font-size:26px;color:{col}'>@cezaevirehberi · {DISCLAIMER if light else 'Hukuki tavsiye değildir'}</span>"
            f"<span style='font-size:26px;font-weight:600'>{e(right)}</span></div>")


def dots(i, n):
    out = []
    for k in range(n):
        w = 44 if k == i else 14
        c = INK if k == i else "#D8D2C5"
        out.append(f"<div style='width:{w}px;height:14px;border-radius:7px;background:{c}'></div>")
    return "<div style='display:flex;gap:10px'>" + "".join(out) + "</div>"


def cover(cat, t):
    title = e(t["title"])
    size = 118 if len(t["title"]) < 45 else 96
    inner = (f"<div style='display:flex;align-items:center;justify-content:space-between'>"
             f"<div style='display:flex;align-items:center;gap:20px'>{LOGO.format(s=72, c=GOLD_D)}"
             f"<span style='font-family:{SERIF};font-size:34px;font-weight:600'>Cezaevi Rehberi</span></div>"
             f"<span style='font-size:24px;font-weight:600;color:{MUTED};letter-spacing:3px'>{e(cat.upper())}</span></div>"
             f"<div style='display:flex;flex-direction:column;gap:44px'>"
             f"<h1 style='margin:0;font-family:{SERIF};font-weight:600;font-size:{size}px;line-height:1.05;letter-spacing:-1.5px'>{title}</h1>"
             f"<div style='width:120px;height:6px;border-radius:3px;background:{GOLD_D}'></div>"
             f"<p style='margin:0;font-size:40px;line-height:1.45;color:#D9E0E8;max-width:840px'>{e(t.get('summary',''))}</p></div>"
             f"<div style='display:flex;align-items:center;justify-content:space-between;border-top:1px solid rgba(246,244,239,0.18);padding-top:36px'>"
             f"<span style='font-size:26px;color:{MUTED}'>@cezaevirehberi</span>"
             f"<span style='font-size:28px;font-weight:600'>Kaydırın →</span></div>")
    return frame(inner, NAVY, PAPER)


def item_html(kind, text, fs):
    if kind == "tip":
        return (f"<div style='background:#EEF2F7;border-radius:24px;padding:28px 32px;display:flex;flex-direction:column;gap:10px'>"
                f"<span style='font-size:22px;font-weight:600;letter-spacing:2px;color:{INKSOFT}'>İPUCU</span>"
                f"<p style='margin:0;font-size:{fs-4}px;line-height:1.45'>{e(text)}</p></div>")
    if kind == "warning":
        return (f"<div style='background:#FBEFE6;border-radius:24px;padding:28px 32px;display:flex;flex-direction:column;gap:10px'>"
                f"<span style='font-size:22px;font-weight:600;letter-spacing:2px;color:#8A4516'>DİKKAT</span>"
                f"<p style='margin:0;font-size:{fs-4}px;line-height:1.45;color:#5E2F0F'>{e(text)}</p></div>")
    if kind == "body":
        return f"<p style='margin:0;font-size:{fs}px;line-height:1.5;color:#26384F'>{e(text)}</p>"
    mark = (f"<span style='flex-shrink:0;width:48px;height:48px;border-radius:24px;background:{INK};color:{PAPER};font-size:24px;font-weight:600;display:flex;align-items:center;justify-content:center'>{kind[4:]}</span>"
            if kind.startswith("step") else
            f"<span style='flex-shrink:0;width:14px;height:14px;border-radius:7px;background:{GOLD_L};margin-top:{fs//2}px'></span>")
    return f"<div style='display:flex;gap:24px;align-items:flex-start'>{mark}<p style='margin:0;font-size:{fs}px;line-height:1.45'>{e(text)}</p></div>"


def inner_page(label, heading, items, idx, total, cont):
    total_len = sum(len(t) for _, t in items)
    fs = 36 if total_len < 330 else (32 if total_len < 520 else 30)
    body = "".join(item_html(k, t, fs) for k, t in items)
    head = e(heading) + (" <span style='color:#8A96A6;font-weight:400'>(devam)</span>" if cont else "")
    inner = (f"<div style='display:flex;align-items:center;justify-content:space-between'>"
             f"<span style='font-size:24px;font-weight:600;letter-spacing:3px;color:{INKSOFT}'>{e(label.upper())}</span>{dots(idx, total)}</div>"
             f"<div style='display:flex;flex-direction:column;gap:40px'>"
             f"<h2 style='margin:0;font-family:{SERIF};font-weight:600;font-size:76px;line-height:1.08;letter-spacing:-1px'>{head}</h2>"
             f"<div style='display:flex;flex-direction:column;gap:30px'>{body}</div></div>"
             + footer(True, f"{idx+1} / {total}"))
    return frame(inner, PAPER, INK)


def end_page(idx, total):
    inner = (f"<div style='display:flex;justify-content:flex-end'>{''}</div>"
             f"<div style='display:flex;flex-direction:column;gap:44px;align-items:flex-start'>{LOGO.format(s=160, c=GOLD_D)}"
             f"<h2 style='margin:0;font-family:{SERIF};font-weight:600;font-size:92px;line-height:1.05;letter-spacing:-1px'>Ayrıntılar ve diğer konular uygulamada</h2>"
             f"<p style='margin:0;font-size:38px;line-height:1.45;color:#D9E0E8'>Cezaevi Rehberi App Store'da ücretsiz. Bağlantı profilde.</p></div>"
             f"<div style='display:flex;align-items:center;justify-content:space-between;border-top:1px solid rgba(246,244,239,0.18);padding-top:36px'>"
             f"<span style='font-size:26px;color:{MUTED}'>@cezaevirehberi · Hukuki tavsiye değildir</span>"
             f"<span style='font-size:26px;font-weight:600'>{idx+1} / {total}</span></div>")
    return frame(inner, NAVY, PAPER)


def story_page(heading, text, kind):
    label = "BİLİYOR MUYDUNUZ?" if kind == "tip" else "DİKKAT"
    size = 64 if len(text) < 160 else 52
    inner = (f"<div style='display:flex;align-items:center;gap:22px'>{LOGO.format(s=76, c=GOLD_D)}"
             f"<span style='font-size:30px;font-weight:600;color:{GOLD_D};letter-spacing:4px'>{label}</span></div>"
             f"<div style='background:{PAPER};color:{INK};border-radius:44px;padding:72px 64px;display:flex;flex-direction:column;gap:32px'>"
             f"<span style='font-size:28px;font-weight:600;letter-spacing:2px;color:{INKSOFT}'>{e(heading.upper())}</span>"
             f"<p style='margin:0;font-family:{SERIF};font-weight:600;font-size:{size}px;line-height:1.2'>{e(text)}</p></div>"
             f"<div style='display:flex;flex-direction:column;align-items:center;gap:20px'>"
             f"<span style='font-size:32px;font-weight:600'>Ayrıntılar Cezaevi Rehberi uygulamasında</span>"
             f"<span style='font-size:28px;color:{MUTED}'>@cezaevirehberi · Hukuki tavsiye değildir</span></div>")
    return frame(inner, NAVY, PAPER, 1080, 1920, "260px 96px 300px")


def shoot(pages, outdir, prefix, w, h):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    outdir.mkdir(parents=True, exist_ok=True)
    paths = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for i, doc in enumerate(pages, 1):
            hp = outdir / f"{prefix}-{i:02d}.html"; hp.write_text(doc)
            pg = b.new_page(viewport={"width": w, "height": h})
            pg.goto(hp.resolve().as_uri()); pg.wait_for_timeout(300)
            png = outdir / f"{prefix}-{i:02d}.png"; pg.screenshot(path=str(png)); pg.close()
            jpg = png.with_suffix(".jpg"); Image.open(png).convert("RGB").save(jpg, quality=93)
            paths.append(str(jpg.resolve()))
        b.close()
    return paths


def make_post(content, state, outdir):
    T = topics(content)
    n = state.get("posts", 0)
    if n % 7 == 6:  # haftada bir uygulama tanıtımı
        promo = PROMOS[state.get("promo_i", 0) % len(PROMOS)]
        cap = PROMO_CAPTIONS[promo] + f"\n\n{DISCLAIMER}\n\n{TAGS}"
        return {"type": "promo", "promo": promo, "images": [str((HERE / promo).resolve())], "caption": cap}
    order = [x for x in ALLOWED_TOPICS if x in T and not T[x][1].get("pro")]
    used = state.get("used_topics", [])
    remaining = [x for x in order if x not in used] or order
    tid = remaining[0]
    cat, t = T[tid]
    pages_spec = []
    for s in t["sections"]:
        for j, part in enumerate(chunk(section_items(s))):
            pages_spec.append((s.get("heading") or t["title"], part, j > 0))
    pages_spec = pages_spec[:8]  # kapak + 8 + kapanış = en fazla 10
    total = len(pages_spec) + 2
    docs = [cover(cat, t)] + [inner_page(t["title"] if len(t["title"]) < 34 else cat, h, it, i + 1, total, c)
                              for i, (h, it, c) in enumerate(pages_spec)] + [end_page(total - 1, total)]
    imgs = shoot(docs, outdir, tid, 1080, 1350)
    cap = f"{t['title']}\n{t.get('summary','')}\n\nAdım adım anlatım için kaydırın. Kaynaklar ve ayrıntılar Cezaevi Rehberi uygulamasında; bağlantı profilde.\n\n{DISCLAIMER}\n\n{TAGS}"
    return {"type": "carousel", "topic": tid, "images": imgs, "caption": cap}


def make_story(content, state, outdir):
    T = topics(content)
    pool = []
    for tid in ALLOWED_TOPICS:
        if tid not in T or T[tid][1].get("pro"):
            continue
        for s in T[tid][1]["sections"]:
            for k in ("tip", "warning"):
                if s.get(k):
                    pool.append((f"{tid}|{s.get("heading","")}|{k}", T[tid][1]["title"], s[k], k))
    used = state.get("used_stories", [])
    rem = [p for p in pool if p[0] not in used] or pool
    key, heading, text, kind = rem[0]
    imgs = shoot([story_page(heading, text, kind)], outdir, "story", 1080, 1920)
    return {"type": "story", "key": key, "images": imgs}


def commit(state_path, plan_path):
    st = load(state_path, {})
    plan = json.loads(pathlib.Path(plan_path).read_text())
    today = datetime.date.today().isoformat()
    if plan["type"] == "story":
        st.setdefault("used_stories", []).append(plan["key"])
        st.setdefault("log", []).append({"date": today, "story": plan["key"]})
    else:
        st["posts"] = st.get("posts", 0) + 1
        if plan["type"] == "promo":
            st["promo_i"] = st.get("promo_i", 0) + 1
            st.setdefault("log", []).append({"date": today, "post": plan["promo"]})
        else:
            ut = st.setdefault("used_topics", [])
            if len(set(ut)) >= len(ALLOWED_TOPICS):
                ut.clear()
            ut.append(plan["topic"])
            st.setdefault("log", []).append({"date": today, "post": plan["topic"]})
    if len(st.get("used_stories", [])) > 200:
        st["used_stories"] = st["used_stories"][-50:]
    pathlib.Path(state_path).write_text(json.dumps(st, ensure_ascii=False, indent=1))
    print("kaydedildi:", state_path)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "commit":
        commit(sys.argv[2], sys.argv[3]); sys.exit()
    content = json.loads(pathlib.Path(sys.argv[2]).read_text())
    state = load(sys.argv[3], {})
    out = pathlib.Path(sys.argv[4])
    plan = make_post(content, state, out) if mode == "post" else make_story(content, state, out)
    (out).mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(json.dumps(plan, ensure_ascii=False, indent=1))
