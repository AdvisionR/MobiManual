---
title: Kiosk modes
class: ai-drafted
area: kiosk-modes
---

# Kiosk modes

A kiosk policy restricts a device to a defined set of applications. It is used
for devices with a single purpose — a scanner in a warehouse, a display in a
waiting area, a device handed to a customer.

## Add a kiosk policy

**Policies >> Kiosk >> Add** opens the interface for adding a kiosk policy.

1. Enter the *Policy name*.
2. Select the *Mode*:
   - *Single app* — the device runs one application and cannot be left.
   - *Multi app* — the selected applications are shown on a restricted home
     screen.
3. Select the applications to be allowed. At least one application must be
   selected.
4. Set the behaviour of the hardware keys and of the status bar.
5. Select *Save*.

The policy is applied to the devices or groups it is assigned to. Assignment is
described under **Policies >> Assignment**.

![Samsung kiosk mode settings](../../images/_samsung_kiosk_Mode_1.png)

## Leaving kiosk mode

A device in kiosk mode cannot be left by its user. To release a device, remove
the kiosk policy from the device or from the group holding it. The device
returns to its normal home screen at the next check-in.
