# Passcode Policy

A passcode policy sets the rules for the passcode that unlocks a device. It
applies to the device passcode, not to console passwords.

| Setting | Values | Default |
|---|---|---|
| **Minimum length** | 4 to 16 characters | 6 |
| **Require letters and digits** | on or off | off |
| **Maximum age (days)** | 0 to 730; 0 means never | 90 |
| **Failed attempts before wipe** | 0 to 20; 0 means never | 10 |

When a passcode reaches its maximum age, the device asks the user for a new
one at the next unlock.

After the set number of failed attempts, the device wipes itself. This cannot
be undone.

If a user has forgotten the passcode, send **Clear passcode** from the device's
**Commands** tab.
