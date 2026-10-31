# Cezaevi Rehberi – Instagram otomatik paylaşım

GitHub Actions her gün @cezaevirehberi hesabında paylaşım yapar (Mac gerekmez):

- 12:06 (İstanbul) hikâye, 19:35 gönderi; pazartesi 06:00 erişim anahtarı yenilenir.
- İçerik, uygulamanın yayımlanan `content.json` dosyasından birebir alınır (https://gunduzenes-droid.github.io/cezaevi-rehberi/content.json).
- Görseller `instagram/ig_render.py` ile üretilir; paylaşım geçmişi `instagram/durum.json`.
- İnfaz Süreci, hukuki süreç ve Pro konular paylaşılmaz; örnek ceza/oran içeren içerik yoktur.

Gerekli secret'lar: `IG_TOKEN` (Instagram erişim anahtarı), `GH_PAT` (anahtar yenileme için, yalnızca bu depoda Secrets: write).

Elle çalıştırma: Actions → "Instagram otomatik paylaşım" → Run workflow → mode: post | story | refresh.
