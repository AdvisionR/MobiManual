# Device Commands

Commands act on a device remotely. They are sent from a device's
**Commands** tab, or to several devices at once from the device list. This page
lists every command, where it runs, and who may send it.

| Command | Android | iOS | Who may send it |
|---|---|---|---|
| **Lock** | yes | yes | Administrator, Helpdesk |
| **Ring** | yes | no | Administrator, Helpdesk |
| **Clear passcode** | yes | supervised only | Administrator, Helpdesk |
| **Update OS** | no | supervised only | Administrator |
| **Retire** | yes | yes | Administrator |
| **Wipe** | yes | yes | Administrator |

## What each command does

- **Lock** locks the screen. The user unlocks it with the device passcode.
- **Ring** plays a sound for 2 minutes, even when the device is muted.
- **Clear passcode** removes the device passcode, so the user can set a new one.
  A passcode policy still requires one at the next unlock.
- **Update OS** installs the iOS update the device has downloaded.
- **Retire** removes the management profile, the policies and the apps
  MobiVisor installed. Personal data stays on the device.
- **Wipe** erases the device and restores its factory settings. Before a wipe
  is queued, the console asks for your password. A wipe cannot be undone.

## Delivery

A command waits in a queue until the device checks in. Android devices check in
every 15 minutes. iOS devices are woken by a push notification, which needs a
valid Apple Push certificate (see Settings).

A command that the device has not acknowledged within 24 hours expires. Expired
commands can be sent again with **Retry** on the device's **Commands** tab.
