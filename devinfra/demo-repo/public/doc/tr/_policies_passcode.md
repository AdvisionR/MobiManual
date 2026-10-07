# Parola Politikası

Parola politikası, bir cihazın kilidini açan parolanın kurallarını belirler.
Konsol şifreleri için değil, cihaz parolası için geçerlidir.

| Ayar | Değerler | Varsayılan |
|---|---|---|
| **Minimum uzunluk** | 4 ile 16 karakter | 6 |
| **Harf ve rakam zorunlu** | açık veya kapalı | kapalı |
| **Maksimum süre (gün)** | 0 ile 730; 0 hiçbir zaman anlamına gelir | 90 |
| **Silmeden önce başarısız deneme sayısı** | 0 ile 20; 0 hiçbir zaman anlamına gelir | 10 |

Bir parola maksimum süresine ulaştığında cihaz, bir sonraki kilit açmada
kullanıcıdan yeni bir parola ister.

Belirlenen sayıda başarısız denemeden sonra cihaz kendini siler. Bu işlem geri
alınamaz.

Kullanıcı parolasını unuttuysa, cihazın **Komutlar** sekmesinden
**Parolayı temizle** gönderin.
