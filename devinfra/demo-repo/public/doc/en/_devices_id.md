# Device Details

Selecting a device opens its detail page, which shows the applied policies,
the installed applications, and the command history, each on its own tab.

## Overview

The **Overview** tab shows the model, the OS version, the serial number, the
owner, the department, the group and the last check-in.

It also shows whether the device is compliant. A non-compliant device lists the
reasons, for example a policy it has not applied yet.

The department comes from the directory. Select **Edit** next to it to change
it. Departments are used in reports; they do not affect policies, which follow
the group.

## Commands

![](img/commands_for_ios_devices.png)

The **Commands** tab offers the commands this device supports. Commands it does
not support are greyed out. See Device Commands for what each one does.

Commands are queued and delivered when the device next checks in. A command
that is not acknowledged within 24 hours is marked as expired. Select **Retry**
next to an expired command to queue it again.

**Retire** removes the device from management and keeps the user's data. A
retired device disappears from the device list while the enrolled filter is on.
