# Cihaz Komutları

Komutlar bir cihaz üzerinde uzaktan işlem yapar. Bir cihazın **Komutlar**
sekmesinden ya da cihaz listesinden aynı anda birden fazla cihaza gönderilir.
Bu sayfa tüm komutları, nerede çalıştıklarını ve kimlerin gönderebileceğini
listeler.

| Komut | Android | iOS | Kim gönderebilir |
|---|---|---|---|
| **Kilitle** | evet | evet | Yönetici, Yardım Masası |
| **Çaldır** | evet | hayır | Yönetici, Yardım Masası |
| **Parolayı temizle** | evet | yalnızca denetimli | Yönetici, Yardım Masası |
| **İşletim sistemini güncelle** | hayır | yalnızca denetimli | Yönetici |
| **Kullanımdan kaldır** | evet | evet | Yönetici |
| **Tamamen sil** | evet | evet | Yönetici |

## Komutlar ne yapar

- **Kilitle** ekranı kilitler. Kullanıcı kilidi cihaz parolasıyla açar.
- **Çaldır**, cihaz sessizde olsa bile 2 dakika boyunca ses çalar.
- **Parolayı temizle**, kullanıcının yenisini belirleyebilmesi için cihaz
  parolasını kaldırır. Bir parola politikası, bir sonraki kilit açmada yine de
  parola ister.
- **İşletim sistemini güncelle**, cihazın indirdiği iOS güncellemesini kurar.
- **Kullanımdan kaldır**, yönetim profilini, politikaları ve MobiVisor'ın
  kurduğu uygulamaları kaldırır. Kişisel veriler cihazda kalır.
- **Tamamen sil**, cihazı siler ve fabrika ayarlarına döndürür. Komut kuyruğa
  alınmadan önce konsol şifrenizi sorar. Bu işlem geri alınamaz.

## Teslim

Bir komut, cihaz bağlanana kadar kuyrukta bekler. Android cihazlar 15 dakikada
bir bağlanır. iOS cihazlar, geçerli bir Apple Push sertifikası gerektiren bir
anlık bildirimle uyandırılır (bkz. Ayarlar).

Cihazın 24 saat içinde onaylamadığı bir komutun süresi dolar. Süresi dolan
komutlar, cihazın **Komutlar** sekmesindeki **Yeniden dene** ile tekrar
gönderilebilir.
