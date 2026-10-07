# Android Kısıtlamaları

Kısıtlamalar, Android cihazlarda cihaz özelliklerini açar veya kapatır. Bazıları
yalnızca tam yönetimli cihazlara uygulanır; son sütuna bakın.

Aşağıdaki tablo `scripts/render-restrictions.js` tarafından kısıtlama şemasından
üretilir. Tabloyu değil şemayı düzenleyin.

<!-- begin generated: android-restrictions -->
| Ayar | Anahtar | Varsayılan | Geçerli olduğu |
|---|---|---|---|
| Allow camera | `camera_enabled` | `true` | fully-managed, work-profile |
| Allow screen capture | `screen_capture_enabled` | `true` | fully-managed, work-profile |
| Allow Bluetooth | `bluetooth_enabled` | `true` | fully-managed |
| Allow USB file transfer | `usb_file_transfer_enabled` | `false` | fully-managed |
| Allow apps from unknown sources | `unknown_sources_enabled` | `false` | fully-managed, work-profile |
| Allow factory reset | `factory_reset_enabled` | `false` | fully-managed |
<!-- end generated: android-restrictions -->

Değiştirilen kısıtlamalar cihaza bir sonraki bağlantısında ulaşır.
