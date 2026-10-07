# App Installations

App Installations puts apps on the devices of chosen groups. Android apps come
from managed Google Play. iOS apps come from the App Store, with licences bought
through Apple Business Manager.

![](screenshots/_appinstallations_1.png)

## Installing an app

1. Open **App Installations** and select **New installation**.
2. Search for the app and choose it.
3. Choose **Required** or **Available**.
4. Choose the groups.
5. Select **Save**.

A **Required** app is installed automatically and the user cannot remove it. An
**Available** app appears in the MobiVisor Agent catalogue, and the user decides
whether to install it.

## Installation status

Each installation lists its devices with a status: **Pending**,
**Installing**, **Installed** or **Failed**.

A failed installation is retried 3 times, an hour apart. If it still fails,
select **Retry** next to the device.

## Removing an app

Select **Remove from devices**. Required apps are uninstalled at the next
check-in. Available apps that users installed stay on their devices.
