# Kullanıcılar

Kullanıcılar sayfası, konsolda oturum açabilen tüm hesapları giriş adı, e-posta
adresi, rol ve kaynakla birlikte listeler. Kaynak, burada oluşturulan hesaplar
için **Yerel**, dizinden aktarılan hesaplar için **LDAP** olur.

![](screenshots/users_page-should_list_accounts.png)

## Kullanıcı ekleme

1. **Kullanıcılar** sayfasını açın ve **Ekle** seçin.
2. Giriş adını ve e-posta adresini girin.
3. Bir rol seçin. Rol, kullanıcının hangi sayfaları açabileceğini belirler.
4. **Kaydet** seçin.

Yeni kullanıcı, şifre belirlemesi için bir bağlantı içeren e-posta alır.
Bağlantı bir kez kullanılabilir ve 48 saat geçerlidir.

## Roller

| Rol | Yapabilecekleri |
|---|---|
| Yönetici | Ayarlar, cihazları kullanımdan kaldırma ve tamamen silme ile Denetim Günlüğü dahil her şey |
| Yardım Masası | Cihazları, grupları, politikaları, uygulamaları ve kullanıcıları görüntüleme; cihazları gruplar arasında taşıma; bir cihazın departmanını belirleme; **Kilitle**, **Çaldır** ve **Parolayı temizle** gönderme |
| Denetçi | Cihazları, grupları, politikaları, uygulamaları ve kullanıcıları görüntüleme ve Denetim Günlüğünü okuma |

Yalnızca yöneticiler kullanıcı ekleyebilir veya bir kullanıcının rolünü
değiştirebilir.

## LDAP'tan aktarma

Yapılandırılmış dizinden hesapları okumak için **Aktar** seçin. Mevcut hesaplar
giriş adına göre eşleştirilir ve tekrar oluşturulmaz. Aktarılan hesaplar, bir
yönetici değiştirene kadar Denetçi rolünü alır.

Dizin **Ayarlar > Dizin** altında yapılandırılır.

## Kullanıcıyı devre dışı bırakma

Bir hesabın yanındaki **Devre dışı bırak** seçeneğini seçin. Devre dışı
bırakılan kullanıcı artık oturum açamaz; kaydettiği cihazlar yönetilmeye devam
eder. **Etkinleştir** ile tekrar oturum açabilir.

## Şifre sıfırlama

Yerel bir hesabın yanındaki **Şifreyi sıfırla** seçeneğini seçin. Kullanıcı,
yeni şifre belirlemesi için 48 saat geçerli bir bağlantı içeren e-posta alır.
Yeni şifre en az 8 karakterden oluşmalı ve bir harf ile bir rakam içermelidir.

Dizindeki hesaplar şifrelerini dizinde değiştirir.
