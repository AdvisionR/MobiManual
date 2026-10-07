# iOS Enrollment

iOS devices are enrolled through Apple Business Manager.

Before you start, check that the Apple Push certificate is valid: without it,
iOS devices cannot be reached (see Settings).

1. Open **Enrollment > iOS**.
2. Choose whether the device is supervised.
3. Decide whether the user may remove the management profile.
4. Choose the group the devices join.
5. Select **Finish** to assign the profile.

Devices already assigned to another server must be released in Apple Business
Manager before they can be assigned here.

## Supervised devices

Supervision gives MobiVisor more control over a device. Some commands and
policies need it: **Update OS**, **Clear passcode**, and single-app kiosk mode
on iOS. Supervision can only be set when the device is enrolled.
