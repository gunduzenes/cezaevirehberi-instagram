# Cezaevi Rehberi – Instagram otomatik paylaşım

GitHub Actions her gün @cezaevirehberi hesabında paylaşım yapar (Mac gerekmez):

- 12:06 (İstanbul) hikâye, 19:35 gönderi; pazartesi 06:00 erişim anahtarı yenilenir.
- İçerik, uygulamanın yayımlanan `content.json` dosyasından birebir alınır (https://gunduzenes-droid.github.io/cezaevi-rehberi/content.json).
- Görseller `instagram/ig_render.py` ile üretilir; paylaşım geçmişi `instagram/durum.json`.
- İnfaz Süreci, hukuki süreç ve Pro konular paylaşılmaz; örnek ceza/oran içeren içerik yoktur.

Gerekli secret'lar: `IG_TOKEN` (Instagram erişim anahtarı), `GH_PAT` (anahtar yenileme için, yalnızca bu depoda Secrets: write).

Elle çalıştırma: Actions → "Instagram otomatik paylaşım" → Run workflow → mode: post | story | refresh.

## Emlak Rehberi – @emlakrehberiapp

Aynı depoda ayrı iş akışı (`.github/workflows/emlak.yml`), dosyalar `emlak/` altında.

- Her gün 20:05 (İstanbul) gönderi, 20:45 yedek; pazartesi 06:30 anahtar yenileme.
- İçerik: https://gunduzenes.github.io/emlak-rehberi/content.json (yoksa depo içindeki content.json).
- Haftalık döngü: rehber, sözlük, rehber, piyasa verisi (yalnız veriler güncellendiyse), rehber, sözlük, tanıtım.
- Pro konularda yalnız uygulamada ücretsiz görünen kısım (kısa cevap, açık bölümler, adım başlıkları) paylaşılır.
- Gerekli secret: `IG_TOKEN_EMLAK` (@emlakrehberiapp erişim anahtarı). Eklenmeden iş akışı paylaşım yapmadan geçer.
