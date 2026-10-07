# Ayarlar

Ayarlar yalnızca yöneticilere açıktır.

## Apple Push sertifikası

MobiVisor iOS cihazlara, Apple tarafından verilen bir sertifika gerektiren
Apple'ın anlık bildirim hizmeti üzerinden ulaşır. Sertifika bir yıl geçerlidir.

1. **CSR indir** seçin.
2. Şirketinizin Apple Kimliği ile Apple Push Certificates Portal'da oturum açın
   ve CSR'yi yükleyin.
3. Sertifikayı Apple'dan indirin ve **Sertifika yükle** seçin.

![](img/apple_push_portal.png)

Sertifikayı süresi dolmadan, aynı Apple Kimliği ile yenileyin. Başka bir Apple
Kimliği ile oluşturulan sertifika zaten kayıtlı cihazlara ulaşamaz ve hepsinin
yeniden kaydedilmesi gerekir. Gösterge Paneli, bitiş tarihinden 30 gün önce
uyarır.

## Dizin

LDAP dizininizin **Sunucu URL'si**, **Temel DN** ve **Bağlanan kullanıcı**
bilgilerini girin, ardından **Bağlantıyı test et** ve **Kaydet** seçin. Dizin,
Kullanıcılar sayfasındaki **Aktar** ve cihaz departmanları için kullanılır.

## E-posta bildirimleri

**SMTP sunucusu** ve **Gönderen adresi** bilgilerini girin. MobiVisor yeni
hesaplar, şifre sıfırlamaları ve Apple Push sertifikası uyarısı için e-posta
gönderir.

## Güvenlik

**Oturum zaman aşımı (dakika)**, konsolun işlem yapılmadan ne kadar süre açık
kalacağını belirler: 5 ile 120 dakika arası. Varsayılan 30'dur.
