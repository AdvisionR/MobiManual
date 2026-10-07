# Android Enrollment

Android devices are enrolled in one of two ways:

- **Fully managed**, for company-owned devices. The whole device is managed. It
  is enrolled during setup, from a QR code.
- **Work profile**, for personally owned devices. Only a separate work profile
  is managed; the user's own apps and data stay private.

## Enrolling fully managed devices

1. Open **Enrollment > Android** and select **Fully managed**.
2. Choose the group the devices join.
3. Select **Create QR code**.
4. On a new or factory-reset device, tap the welcome screen six times and scan
   the code.

![](screenshots/_android_qr_code_1.png)

A QR code can enroll any number of devices and is valid for 7 days.

## Enrolling a work profile

1. Open **Enrollment > Android** and select **Work profile**.
2. Choose the group the device joins.
3. Select **Create token** and give the token to the user.
4. The user installs MobiVisor Agent from Google Play and enters the token.

A token enrolls one device and is valid for 7 days.
