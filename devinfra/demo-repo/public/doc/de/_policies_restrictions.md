# Android-Einschränkungen

Einschränkungen schalten Gerätefunktionen auf Android-Geräten ein oder aus.
Manche gelten nur für vollständig verwaltete Geräte; siehe die letzte Spalte.

Die folgende Tabelle wird von `scripts/render-restrictions.js` aus dem
Einschränkungsschema erzeugt. Bearbeiten Sie das Schema, nicht die Tabelle.

<!-- begin generated: android-restrictions -->
| Einstellung | Schlüssel | Standard | Gilt für |
|---|---|---|---|
| Allow camera | `camera_enabled` | `true` | fully-managed, work-profile |
| Allow screen capture | `screen_capture_enabled` | `true` | fully-managed, work-profile |
| Allow Bluetooth | `bluetooth_enabled` | `true` | fully-managed |
| Allow USB file transfer | `usb_file_transfer_enabled` | `false` | fully-managed |
| Allow apps from unknown sources | `unknown_sources_enabled` | `false` | fully-managed, work-profile |
| Allow factory reset | `factory_reset_enabled` | `false` | fully-managed |
<!-- end generated: android-restrictions -->

Geänderte Einschränkungen erreichen ein Gerät beim nächsten Check-in.
