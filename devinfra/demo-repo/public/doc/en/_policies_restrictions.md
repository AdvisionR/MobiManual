# Android Restrictions

Restrictions turn device features on or off for Android devices. Some apply only
to fully managed devices; see the last column.

The table below is generated from the restriction schema by
`scripts/render-restrictions.js`. Edit the schema, not the table.

<!-- begin generated: android-restrictions -->
| Setting | Key | Default | Applies to |
|---|---|---|---|
| Allow camera | `camera_enabled` | `true` | fully-managed, work-profile |
| Allow screen capture | `screen_capture_enabled` | `true` | fully-managed, work-profile |
| Allow Bluetooth | `bluetooth_enabled` | `true` | fully-managed |
| Allow USB file transfer | `usb_file_transfer_enabled` | `false` | fully-managed |
| Allow apps from unknown sources | `unknown_sources_enabled` | `false` | fully-managed, work-profile |
| Allow factory reset | `factory_reset_enabled` | `false` | fully-managed |
<!-- end generated: android-restrictions -->

Changed restrictions reach a device at its next check-in.
