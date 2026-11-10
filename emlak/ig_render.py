"""
Emlak Rehberi Instagram görsel üretici (@emlakrehberiapp hesabı için).

Kullanım:
  python3 ig_render.py post   <content.json> <durum.json> <cikti_klasoru>
  python3 ig_render.py story  <content.json> <durum.json> <cikti_klasoru>
  python3 ig_render.py commit <durum.json> <cikti_klasoru>/plan.json   (paylaşım başarılı olduktan sonra)

Kurallar
- Metinler uygulamanın content.json dosyasından BİREBİR alınır; hiçbir metin uydurulmaz.
- Pro konularda yalnızca uygulamada ücretsiz görünen kısım paylaşılır: kısa cevap,
  `freeSections` kadar bölüm ve adımların yalnız başlıkları. Ayrıntılar "uygulamada" denerek bırakılır.
- Mahkeme kararı içeriği yoktur (uygulamada da yok).
- "Av. Enes Gündüz" adı hiçbir görselde veya açıklamada geçmez.

Haftalık döngü (gönderi sayacına göre): rehber, sözlük, rehber, piyasa verisi, rehber, sözlük, tanıtım.
Piyasa verisi yalnızca market.asOf değiştiyse paylaşılır; değişmediyse o gün rehber paylaşılır.
"""
import json, sys, re, html, pathlib, datetime

HERE = pathlib.Path(__file__).resolve().parent
HANDLE = "@emlakrehberiapp"
APP = "Emlak Rehberi"
DISCLAIMER = "Bilgilendirme amaçlıdır; hukuki, vergi veya yatırım tavsiyesi değildir."
SHORT_DISC = "Tavsiye değildir"
TAGS = "#emlak #emlakrehberi #tapu #kira #konut #kentseldönüşüm #istanbul"
PROMOS = ["promo-tanitim", "promo-hesapla"]
PROMO_CAPTIONS = {
    "promo-tanitim": "Ev alırken, kiralarken ya da kentsel dönüşümde aklınıza takılanlar tek uygulamada: tapu devri, kira artışı, kat mülkiyeti, hisseli tapu, iskân ve daha fazlası. Her konu yürürlükteki mevzuata dayanır; dayanak maddeler yazılıdır.\n\nİstanbul'un güncel konut ve kira göstergeleri de uygulamada (TCMB, TÜİK).\n\nEmlak Rehberi App Store'da. Bağlantı profilde.",
    "promo-hesapla": "Tapu harcı ve kira artışı hesaplayıcıları Emlak Rehberi'nde ücretsiz. Kredi, inşaat maliyeti, emsal, amortisman ve değer artış kazancı vergisi hesaplayıcıları Pro'da.\n\nOranlar ve tutarlar resmî kaynaklardan güncellenir; sonuçlar bilgilendirme amaçlıdır.\n\nEmlak Rehberi App Store'da. Bağlantı profilde.",
}

GREEN, GREEN_D, PAPER, CARD, INK, INKSOFT, LINE, GOLD, GOLD_L, MUTED, TERRA = (
    "#1F4A3E", "#173A31", "#F5F1E9", "#ECE4D8", "#173A31", "#4E6A60", "#E2DBCE", "#C9A45C", "#E6C98A", "#A9C2B8", "#B4602F")
SERIF, SANS = "Lora, Georgia, serif", "Inter, system-ui, sans-serif"
ROOF = ('<svg width="{w}" height="{h}" viewBox="0 0 120 50"><path d="M6 44L60 6l54 38" fill="none" stroke="{c}" '
        'stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def up(t):
    return t.replace("i", "İ").replace("ı", "I").upper()


def e(t):
    return html.escape(t, quote=False)


def md(t):
    """**kalın** işaretini koruyarak kaçışlı HTML üretir."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b style='font-weight:650'>\1</b>", e(t))


def plain(t):
    return re.sub(r"\*\*(.+?)\*\*", r"\1", t)


def load(p, default):
    p = pathlib.Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def all_topics(content):
    out = {}
    for c in content["categories"]:
        for t in c["topics"]:
            out[t["id"]] = (c["title"], t)
    return out


def topic_order(content):
    """Kategoriler arasında dönüşümlü sıra; ücretsiz konular kendi kategorisinde öne alınır."""
    cols = []
    for c in content["categories"]:
        ts = sorted(c["topics"], key=lambda t: bool(t.get("pro")))
        cols.append([t["id"] for t in ts])
    order, i = [], 0
    while any(cols):
        col = cols[i % len(cols)]
        if col:
            order.append(col.pop(0))
        i += 1
    return order


# ---------- çerçeve ----------

def frame(inner, bg, fg, w=1080, h=1350, pad="92px 92px 76px"):
    return (f"<!doctype html><html lang='tr'><head><meta charset='utf-8'><style>body{{margin:0}}b{{font-weight:650}}</style></head><body>"
            f"<div style=\"width:{w}px;height:{h}px;box-sizing:border-box;padding:{pad};background:{bg};color:{fg};font-family:{SANS};"
            f"display:flex;flex-direction:column;justify-content:space-between;position:relative;overflow:hidden\">{inner}</div></body></html>")


def dark_bg():
    return f"radial-gradient(circle at 50% 18%, #2A5C4E 0%, {GREEN} 45%, {GREEN_D} 100%)"


def brand(size=34):
    return (f"<div style='display:flex;align-items:center;gap:18px'>{ROOF.format(w=64, h=27, c=GOLD)}"
            f"<span style='font-family:{SERIF};font-size:{size}px;font-weight:600'>Emlak <span style='color:{GOLD};font-family:{SANS};font-weight:500;font-size:{int(size*0.62)}px;letter-spacing:6px'>REHBERİ</span></span></div>")


def footer(light, right):
    col = INKSOFT if light else MUTED
    border = LINE if light else "rgba(245,241,233,0.18)"
    return (f"<div style='display:flex;align-items:center;justify-content:space-between;border-top:2px solid {border};padding-top:34px'>"
            f"<span style='font-size:25px;color:{col}'>{HANDLE} · {SHORT_DISC}</span>"
            f"<span style='font-size:26px;font-weight:600'>{e(right)}</span></div>")


def dots(i, n):
    out = []
    for k in range(n):
        w = 44 if k == i else 14
        c = INK if k == i else "#D6CEBF"
        out.append(f"<div style='width:{w}px;height:14px;border-radius:7px;background:{c}'></div>")
    return "<div style='display:flex;gap:10px'>" + "".join(out) + "</div>"


def kicker(text, light=True):
    return f"<span style='font-size:24px;font-weight:600;letter-spacing:3px;color:{INKSOFT if light else GOLD}'>{e(up(text))}</span>"


# ---------- rehber gönderisi ----------

def cover(cat, t, scope_note=None):
    size = 112 if len(t["title"]) < 34 else (96 if len(t["title"]) < 52 else 82)
    s = t.get("summary", "")
    sfs = 38 if len(s) < 260 else 33
    badge = (f"<span style='align-self:flex-start;font-size:23px;font-weight:600;letter-spacing:2px;color:{GREEN_D};"
             f"background:{GOLD_L};border-radius:999px;padding:10px 22px'>KISA CEVAP</span>")
    inner = (f"<div style='display:flex;align-items:center;justify-content:space-between'>{brand()}"
             f"<span style='font-size:22px;font-weight:600;color:{MUTED};letter-spacing:3px'>{e(up(cat))}</span></div>"
             f"<div style='display:flex;flex-direction:column;gap:38px'>"
             f"<h1 style='margin:0;font-family:{SERIF};font-weight:600;font-size:{size}px;line-height:1.06;letter-spacing:-1.5px'>{e(t['title'])}</h1>"
             f"<div style='width:120px;height:5px;border-radius:3px;background:{GOLD}'></div>{badge}"
             f"<p style='margin:0;font-size:{sfs}px;line-height:1.48;color:#DCE7E2;max-width:880px'>{md(s)}</p></div>"
             f"<div style='display:flex;align-items:center;justify-content:space-between;border-top:1px solid rgba(245,241,233,0.18);padding-top:34px'>"
             f"<span style='font-size:25px;color:{MUTED}'>{HANDLE}</span>"
             f"<span style='font-size:28px;font-weight:600'>Kaydırın →</span></div>")
    return frame(inner, dark_bg(), PAPER)


def section_items(s, headlines_only=False):
    items = []
    if s.get("body"):
        items.append(("body", s["body"]))
    for i, st in enumerate(s.get("steps", []), 1):
        if headlines_only:
            m = re.match(r"\*\*(.+?)\*\*", st)
            items.append((f"step{i}", f"**{m.group(1)}**" if m else st.split(".")[0] + "."))
        else:
            items.append((f"step{i}", st))
    for b in s.get("bullets", []):
        items.append(("bullet", b))
    for b in s.get("checklist", []):
        items.append(("check", b))
    if s.get("table"):
        items.append(("table", s["table"]))
    if s.get("tip"):
        items.append(("tip", s["tip"]))
    if s.get("warning"):
        items.append(("warning", s["warning"]))
    return items


def ilen(it):
    k, v = it
    if k == "table":
        return sum(len(" ".join(r)) for r in v["rows"]) + 80 * len(v["rows"])
    return len(v) + 60


def chunk(items, budget=700):
    pages, cur, n = [], [], 0
    for it in items:
        if it[0] == "table":
            if cur:
                pages.append(cur); cur, n = [], 0
            rows = it[1]["rows"]
            per = max(1, min(len(rows), 4 if ilen(it) > 900 else 6))
            for i in range(0, len(rows), per):
                pages.append([("table", {"headers": it[1].get("headers", []), "rows": rows[i:i + per]})])
            continue
        L = ilen(it)
        if cur and n + L > budget:
            pages.append(cur); cur, n = [], 0
        cur.append(it); n += L
    if cur:
        pages.append(cur)
    return pages


def table_html(tb, fs):
    th = "".join(f"<th style='text-align:left;padding:14px 16px;font-size:{fs-8}px;letter-spacing:1px;color:{INKSOFT};border-bottom:2px solid {LINE}'>{e(up(h))}</th>"
                 for h in tb.get("headers", []))
    trs = ""
    for r in tb["rows"]:
        tds = "".join(f"<td style='vertical-align:top;padding:16px;font-size:{fs-6}px;line-height:1.38;border-bottom:1px solid {LINE};"
                      f"{'font-weight:600;' if j == 0 else ''}'>{md(c)}</td>" for j, c in enumerate(r))
        trs += f"<tr>{tds}</tr>"
    return f"<table style='border-collapse:collapse;width:100%;background:#fff;border-radius:22px;overflow:hidden'><tr>{th}</tr>{trs}</table>"


def item_html(kind, text, fs):
    if kind == "table":
        return table_html(text, fs)
    if kind in ("tip", "warning"):
        bg, lab, col = ("#E6EFEA", "İPUCU", INKSOFT) if kind == "tip" else ("#F7E9DF", "DİKKAT", "#8A4516")
        return (f"<div style='background:{bg};border-radius:24px;padding:28px 32px;display:flex;flex-direction:column;gap:10px'>"
                f"<span style='font-size:22px;font-weight:600;letter-spacing:2px;color:{col}'>{lab}</span>"
                f"<p style='margin:0;font-size:{fs-4}px;line-height:1.45'>{md(text)}</p></div>")
    if kind == "body":
        return f"<p style='margin:0;font-size:{fs}px;line-height:1.5;color:#26413A'>{md(text)}</p>"
    if kind.startswith("step"):
        mark = (f"<span style='flex-shrink:0;width:50px;height:50px;border-radius:25px;background:{GREEN};color:{PAPER};font-size:24px;"
                f"font-weight:600;display:flex;align-items:center;justify-content:center'>{kind[4:]}</span>")
    elif kind == "check":
        mark = (f"<span style='flex-shrink:0;width:40px;height:40px;border-radius:10px;border:3px solid {GREEN};box-sizing:border-box;"
                f"margin-top:{max(0, fs//2-18)}px'></span>")
    else:
        mark = f"<span style='flex-shrink:0;width:14px;height:14px;border-radius:7px;background:{GOLD};margin-top:{fs//2}px'></span>"
    return f"<div style='display:flex;gap:24px;align-items:flex-start'>{mark}<p style='margin:0;font-size:{fs}px;line-height:1.45'>{md(text)}</p></div>"


def inner_page(label, heading, items, idx, total, cont, note=None):
    tl = sum(ilen(i) for i in items)
    fs = 36 if tl < 360 else (32 if tl < 560 else 30)
    body = "".join(item_html(k, t, fs) for k, t in items)
    if note:
        body += (f"<div style='display:flex;align-items:center;gap:16px;background:{CARD};border-radius:20px;padding:22px 28px'>"
                 f"<span style='font-size:22px;font-weight:700;letter-spacing:2px;color:{TERRA}'>PRO</span>"
                 f"<span style='font-size:27px;line-height:1.4;color:{INKSOFT}'>{e(note)}</span></div>")
    head = e(heading) + (" <span style='color:#8C9C95;font-weight:400'>(devam)</span>" if cont else "")
    hs = 72 if len(heading) < 26 else 60
    inner = (f"<div style='display:flex;align-items:center;justify-content:space-between'>{kicker(label)}{dots(idx, total)}</div>"
             f"<div style='display:flex;flex-direction:column;gap:38px'>"
             f"<h2 style='margin:0;font-family:{SERIF};font-weight:600;font-size:{hs}px;line-height:1.08;letter-spacing:-1px'>{head}</h2>"
             f"<div style='display:flex;flex-direction:column;gap:28px'>{body}</div></div>"
             + footer(True, f"{idx+1} / {total}"))
    return frame(inner, PAPER, INK)


def end_page(idx, total, t=None):
    basis = ""
    if t and t.get("basis"):
        basis = (f"<div style='display:flex;flex-direction:column;gap:12px;border-left:4px solid {GOLD};padding-left:26px'>"
                 f"<span style='font-size:22px;font-weight:600;letter-spacing:3px;color:{GOLD}'>DAYANAK</span>"
                 f"<span style='font-size:28px;line-height:1.45;color:#DCE7E2'>{e(t['basis'])}</span></div>")
    pro_line = "Adımların ayrıntısı, dikkat edilecekler ve hesaplayıcılar uygulamada." if t and t.get("pro") else "Diğer konular, güncel veriler ve hesaplayıcılar uygulamada."
    inner = (f"<div>{brand()}</div>"
             f"<div style='display:flex;flex-direction:column;gap:40px;align-items:flex-start'>"
             f"<h2 style='margin:0;font-family:{SERIF};font-weight:600;font-size:86px;line-height:1.06;letter-spacing:-1px'>Devamı Emlak Rehberi'nde</h2>"
             f"<p style='margin:0;font-size:36px;line-height:1.45;color:#DCE7E2'>{pro_line} Bağlantı profilde.</p>{basis}</div>"
             f"<div style='display:flex;align-items:center;justify-content:space-between;border-top:1px solid rgba(245,241,233,0.18);padding-top:34px'>"
             f"<span style='font-size:25px;color:{MUTED}'>{HANDLE} · {SHORT_DISC}</span>"
             f"<span style='font-size:26px;font-weight:600'>{idx+1} / {total}</span></div>")
    return frame(inner, dark_bg(), PAPER)


def guide_post(content, state, outdir):
    T = all_topics(content)
    order = topic_order(content)
    used = state.get("used_topics", [])
    k = len(used) % len(order)
    recent = used[-k:] if k else []
    remaining = [x for x in order if x not in recent] or order
    tid = remaining[0]
    cat, t = T[tid]
    pro = bool(t.get("pro"))
    specs = []
    secs = t["sections"]
    if not pro:
        for s in secs:
            for j, part in enumerate(chunk(section_items(s))):
                specs.append((s.get("heading") or t["title"], part, j > 0, None))
    else:
        nfree = t.get("freeSections") or 0
        for s in secs[:nfree]:
            for j, part in enumerate(chunk(section_items(s))):
                specs.append((s.get("heading") or t["title"], part, j > 0, None))
        # kilitli bölümlerden yalnızca adım başlıkları
        for s in secs[nfree:]:
            if s.get("steps"):
                its = section_items({"steps": s["steps"]}, headlines_only=True)
                for j, part in enumerate(chunk(its, 900)):
                    specs.append((s.get("heading") or "Adımlar", part, j > 0, None))
                break
        if specs:
            h, part, c, _ = specs[-1]
            specs[-1] = (h, part, c, "Her adımın ayrıntısı ve dikkat edilecekler Emlak Rehberi Pro'da.")
    specs = specs[:7]
    total = len(specs) + 2
    label = t["title"] if len(t["title"]) < 34 else cat
    docs = [cover(cat, t)] + [inner_page(label, h, it, i + 1, total, c, n) for i, (h, it, c, n) in enumerate(specs)] + [end_page(total - 1, total, t)]
    imgs = shoot(docs, outdir, tid, 1080, 1350)
    cap = (f"{t['title']}\n\n{plain(t.get('summary', ''))}\n\n"
           f"{'Adım adım anlatım için kaydırın.' if not pro else 'Adımlar için kaydırın; ayrıntılar uygulamada.'} "
           f"Dayanak: {t.get('basis', '')}\n\n{APP} App Store'da; bağlantı profilde.\n\n{DISCLAIMER}\n\n{TAGS}")
    return {"type": "carousel", "kind": "guide", "topic": tid, "images": imgs, "caption": cap}


# ---------- sözlük ----------

def glossary_page(terms, idx, total):
    cards = ""
    for g in terms:
        cards += (f"<div style='background:#fff;border-radius:26px;padding:34px 38px;display:flex;flex-direction:column;gap:14px'>"
                  f"<span style='font-family:{SERIF};font-size:44px;font-weight:600;color:{GREEN}'>{e(g['term'])}</span>"
                  f"<p style='margin:0;font-size:31px;line-height:1.45'>{md(g['definition'])}.</p>"
                  + (f"<span style='font-size:22px;color:{INKSOFT}'>Dayanak: {e(g['basis'])}</span>" if g.get("basis") else "")
                  + "</div>")
    inner = (f"<div style='display:flex;align-items:center;justify-content:space-between'>{kicker('Emlak sözlüğü')}{dots(idx, total)}</div>"
             f"<div style='display:flex;flex-direction:column;gap:26px'>{cards}</div>" + footer(True, f"{idx+1} / {total}"))
    return frame(inner, PAPER, INK)


def glossary_cover(terms):
    names = "".join(f"<span style='font-family:{SERIF};font-size:64px;font-weight:600;line-height:1.15'>{e(g['term'])}</span>" for g in terms)
    inner = (f"<div style='display:flex;align-items:center;justify-content:space-between'>{brand()}"
             f"<span style='font-size:22px;font-weight:600;color:{MUTED};letter-spacing:3px'>EMLAK SÖZLÜĞÜ</span></div>"
             f"<div style='display:flex;flex-direction:column;gap:30px'>"
             f"<span style='font-size:30px;font-weight:600;letter-spacing:4px;color:{GOLD}'>BU KAVRAMLARI BİLİYOR MUSUNUZ?</span>"
             f"<div style='display:flex;flex-direction:column;gap:12px'>{names}</div>"
             f"<div style='width:120px;height:5px;border-radius:3px;background:{GOLD}'></div></div>"
             f"<div style='display:flex;align-items:center;justify-content:space-between;border-top:1px solid rgba(245,241,233,0.18);padding-top:34px'>"
             f"<span style='font-size:25px;color:{MUTED}'>{HANDLE}</span><span style='font-size:28px;font-weight:600'>Kaydırın →</span></div>")
    return frame(inner, dark_bg(), PAPER)


def glossary_post(content, state, outdir):
    G = content.get("glossary", [])
    i = state.get("gloss_i", 0) % max(1, len(G))
    terms = (G[i:] + G[:i])[:3]
    pages, cur, n = [], [], 0
    for g in terms:
        L = len(g["definition"]) + 120
        if cur and n + L > 1000:
            pages.append(cur); cur, n = [], 0
        cur.append(g); n += L
    pages.append(cur)
    total = len(pages) + 2
    docs = [glossary_cover(terms)] + [glossary_page(p, k + 1, total) for k, p in enumerate(pages)] + [end_page(total - 1, total)]
    imgs = shoot(docs, outdir, f"sozluk-{i:02d}", 1080, 1350)
    lines = "\n".join(f"• {g['term']}: {plain(g['definition'])}." for g in terms)
    cap = f"Emlak sözlüğü\n\n{lines}\n\nUygulamada 30 terimlik sözlük ve arama var; bağlantı profilde.\n\n{DISCLAIMER}\n\n{TAGS}"
    return {"type": "carousel", "kind": "glossary", "gloss_i": i, "images": imgs, "caption": cap}


# ---------- piyasa verisi ----------

def market_page(title, inds, idx, total):
    cards = ""
    for x in inds:
        cards += (f"<div style='background:#fff;border-radius:24px;padding:22px 30px;display:flex;flex-direction:column;gap:6px'>"
                  f"<div style='display:flex;justify-content:space-between;align-items:baseline'>"
                  f"<span style='font-size:27px;font-weight:600;color:{INKSOFT}'>{e(x['title'])}</span>"
                  f"<span style='font-size:21px;color:{INKSOFT}'>{e(x.get('source',''))} · {e(x.get('period',''))}</span></div>"
                  f"<span style='font-family:{SERIF};font-size:54px;font-weight:600;color:{GREEN};line-height:1.05'>{e(x['value'])}</span>"
                  f"<span style='font-size:25px;line-height:1.4;color:#26413A'>{e(x.get('detail',''))}</span></div>")
    inner = (f"<div style='display:flex;align-items:center;justify-content:space-between'>{kicker('Piyasa verileri')}{dots(idx, total)}</div>"
             f"<div style='display:flex;flex-direction:column;gap:22px'>"
             f"<h2 style='margin:0;font-family:{SERIF};font-weight:600;font-size:60px;line-height:1.08'>{e(title)}</h2>{cards}</div>"
             + footer(True, f"{idx+1} / {total}"))
    return frame(inner, PAPER, INK)


def market_cover(m):
    inner = (f"<div style='display:flex;align-items:center;justify-content:space-between'>{brand()}"
             f"<span style='font-size:22px;font-weight:600;color:{MUTED};letter-spacing:3px'>PİYASA VERİLERİ</span></div>"
             f"<div style='display:flex;flex-direction:column;gap:36px'>"
             f"<h1 style='margin:0;font-family:{SERIF};font-weight:600;font-size:104px;line-height:1.05;letter-spacing:-1.5px'>Konut ve kira piyasasında son durum</h1>"
             f"<div style='width:120px;height:5px;border-radius:3px;background:{GOLD}'></div>"
             f"<p style='margin:0;font-size:36px;line-height:1.45;color:#DCE7E2'>İstanbul ve Türkiye göstergeleri · TCMB ve TÜİK verileri · {e(m.get('asOf',''))} itibarıyla</p></div>"
             f"<div style='display:flex;align-items:center;justify-content:space-between;border-top:1px solid rgba(245,241,233,0.18);padding-top:34px'>"
             f"<span style='font-size:25px;color:{MUTED}'>{HANDLE}</span><span style='font-size:28px;font-weight:600'>Kaydırın →</span></div>")
    return frame(inner, dark_bg(), PAPER)


def market_post(content, outdir):
    m = content["market"]
    inds = [x for x in m.get("indicators", []) if x.get("free", True)]
    ist = [x for x in inds if x.get("scope") == "istanbul"]
    tr = [x for x in inds if x.get("scope") != "istanbul"]
    groups = []
    for title, lst in (("İstanbul", ist), ("Türkiye", tr)):
        for k in range(0, len(lst), 5):
            groups.append((title + (" (devam)" if k else ""), lst[k:k + 5]))
    total = len(groups) + 2
    docs = [market_cover(m)] + [market_page(t, l, i + 1, total) for i, (t, l) in enumerate(groups)] + [end_page(total - 1, total)]
    imgs = shoot(docs, outdir, "piyasa", 1080, 1350)
    lines = "\n".join(f"• {'İstanbul' if x.get('scope') == 'istanbul' else 'Türkiye'} – {x['title']}: {x['value']} ({x.get('period','')}, {x.get('source','')})" for x in inds)
    cap = (f"Konut ve kira piyasasında son durum ({m.get('asOf','')} itibarıyla)\n\n{lines}\n\n"
           f"Kaynak: TCMB EVDS ve TÜİK. Uygulamada göstergeler her ay güncellenir; bağlantı profilde.\n\n{DISCLAIMER}\n\n{TAGS}")
    return {"type": "carousel", "kind": "market", "asOf": m.get("asOf"), "images": imgs, "caption": cap}


# ---------- tanıtım ----------

def promo_doc(name):
    if name == "promo-tanitim":
        items = ["Satın alma ve satış", "Kiralama", "Kat mülkiyeti ve site yaşamı", "Kentsel dönüşüm", "İnşaat ve iskân", "Ortak mülkiyet ve aile konutu"]
        head, sub = "Emlakla ilgili her şey, mevzuata dayalı ve tek yerde", "Rehber · Güncel veriler · Hesaplayıcılar"
    else:
        items = ["Tapu harcı (ücretsiz)", "Kira artışı (ücretsiz)", "Konut kredisi", "İnşaat maliyeti", "Emsal (inşaat alanı)", "Değer artış kazancı vergisi"]
        head, sub = "Hesabınızı uygulamada yapın", "Oranlar resmî kaynaklardan güncellenir"
    li = "".join(f"<div style='display:flex;align-items:center;gap:22px'><span style='width:14px;height:14px;border-radius:7px;background:{GOLD}'></span>"
                 f"<span style='font-size:38px'>{e(x)}</span></div>" for x in items)
    inner = (f"<div>{brand(40)}</div>"
             f"<div style='display:flex;flex-direction:column;gap:40px'>"
             f"<h1 style='margin:0;font-family:{SERIF};font-weight:600;font-size:92px;line-height:1.06;letter-spacing:-1px'>{e(head)}</h1>"
             f"<span style='font-size:30px;font-weight:600;letter-spacing:3px;color:{GOLD}'>{e(up(sub))}</span>"
             f"<div style='display:flex;flex-direction:column;gap:22px'>{li}</div></div>"
             f"<div style='display:flex;align-items:center;justify-content:space-between;border-top:1px solid rgba(245,241,233,0.18);padding-top:34px'>"
             f"<span style='font-size:25px;color:{MUTED}'>{HANDLE} · {SHORT_DISC}</span><span style='font-size:28px;font-weight:600'>App Store · Bağlantı profilde</span></div>")
    return frame(inner, dark_bg(), PAPER)


def promo_post(state, outdir):
    name = PROMOS[state.get("promo_i", 0) % len(PROMOS)]
    imgs = shoot([promo_doc(name)], outdir, name, 1080, 1350)
    return {"type": "promo", "kind": "promo", "promo": name, "images": imgs, "caption": PROMO_CAPTIONS[name] + f"\n\n{DISCLAIMER}\n\n{TAGS}"}


# ---------- hikâye ----------

def story_page(label, heading, text, sub):
    size = 62 if len(text) < 170 else (52 if len(text) < 280 else 44)
    inner = (f"<div style='display:flex;align-items:center;justify-content:space-between'>{brand(40)}"
             f"<span style='font-size:28px;font-weight:600;color:{GOLD};letter-spacing:4px'>{e(label)}</span></div>"
             f"<div style='background:{PAPER};color:{INK};border-radius:44px;padding:70px 62px;display:flex;flex-direction:column;gap:30px'>"
             f"<span style='font-size:28px;font-weight:600;letter-spacing:2px;color:{INKSOFT}'>{e(up(heading))}</span>"
             f"<p style='margin:0;font-family:{SERIF};font-weight:600;font-size:{size}px;line-height:1.22'>{md(text)}</p>"
             + (f"<span style='font-size:24px;color:{INKSOFT}'>{e(sub)}</span>" if sub else "") +
             f"</div><div style='display:flex;flex-direction:column;align-items:center;gap:18px'>"
             f"<span style='font-size:32px;font-weight:600'>Ayrıntılar Emlak Rehberi uygulamasında</span>"
             f"<span style='font-size:27px;color:{MUTED}'>{HANDLE} · {SHORT_DISC}</span></div>")
    return frame(inner, dark_bg(), PAPER, 1080, 1920, "250px 92px 290px")


def story_pool(content):
    pool = []
    T = all_topics(content)
    for tid in topic_order(content):
        cat, t = T[tid]
        pool.append((f"ozet|{tid}", "KISA CEVAP", t["title"], t.get("summary", ""), f"Dayanak: {t.get('basis','')}"))
    for g in content.get("glossary", []):
        pool.append((f"terim|{g['term']}", "TERİM", g["term"], g["definition"] + ".", f"Dayanak: {g['basis']}" if g.get("basis") else ""))
    # özet ve terimleri dönüşümlü sırala
    oz = [p for p in pool if p[0].startswith("ozet")]
    te = [p for p in pool if p[0].startswith("terim")]
    mixed = []
    for i in range(max(len(oz), len(te))):
        if i < len(te): mixed.append(te[i])
        if i < len(oz): mixed.append(oz[i])
    return mixed


def make_story(content, state, outdir):
    pool = story_pool(content)
    used = state.get("used_stories", [])
    k = len(used) % len(pool)
    recent = used[-k:] if k else []
    rem = [p for p in pool if p[0] not in recent] or pool
    key, label, heading, text, sub = rem[0]
    imgs = shoot([story_page(label, heading, text, sub)], outdir, "story", 1080, 1920)
    return {"type": "story", "key": key, "images": imgs}


# ---------- ortak ----------

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
            # taşma kontrolü
            over = pg.evaluate("() => { const d = document.body.firstElementChild; return d.scrollHeight > d.clientHeight + 2 }")
            if over:
                print(f"UYARI: taşma {hp.name}", file=sys.stderr)
            png = outdir / f"{prefix}-{i:02d}.png"; pg.screenshot(path=str(png)); pg.close()
            jpg = png.with_suffix(".jpg"); Image.open(png).convert("RGB").save(jpg, quality=93)
            png.unlink(); hp.unlink()
            paths.append(str(jpg.resolve()))
        b.close()
    return paths


def make_post(content, state, outdir):
    n = state.get("posts", 0)
    slot = n % 7
    if slot == 6:
        return promo_post(state, outdir)
    if slot in (1, 5) and content.get("glossary"):
        return glossary_post(content, state, outdir)
    if slot == 3 and content.get("market", {}).get("asOf") and content["market"]["asOf"] != state.get("market_asof"):
        return market_post(content, outdir)
    return guide_post(content, state, outdir)


def commit(state_path, plan_path):
    st = load(state_path, {})
    plan = json.loads(pathlib.Path(plan_path).read_text())
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).date().isoformat()
    if plan["type"] == "story":
        st.setdefault("used_stories", []).append(plan["key"])
        st.setdefault("log", []).append({"date": today, "story": plan["key"]})
    else:
        st["posts"] = st.get("posts", 0) + 1
        k = plan.get("kind")
        if k == "promo":
            st["promo_i"] = st.get("promo_i", 0) + 1
            st.setdefault("log", []).append({"date": today, "post": plan["promo"]})
        elif k == "glossary":
            st["gloss_i"] = plan["gloss_i"] + 3
            st.setdefault("log", []).append({"date": today, "post": f"sozluk-{plan['gloss_i']}"})
        elif k == "market":
            st["market_asof"] = plan["asOf"]
            st.setdefault("log", []).append({"date": today, "post": f"piyasa-{plan['asOf']}"})
        else:
            ut = st.setdefault("used_topics", [])
            ut.append(plan["topic"])
            st.setdefault("log", []).append({"date": today, "post": plan["topic"]})
    if len(st.get("used_stories", [])) > 300:
        st["used_stories"] = st["used_stories"][-60:]
    if len(st.get("log", [])) > 400:
        st["log"] = st["log"][-120:]
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
    out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(json.dumps(plan, ensure_ascii=False, indent=1))
