---
title: Enrolling iOS devices with Apple Business Manager
class: ai-drafted
area: enrollment-ios
---

# Enrolling iOS devices with Apple Business Manager

Devices purchased through Apple Business Manager (ABM) can be enrolled without
being touched by an administrator. The device is assigned to MobiVisor in ABM,
and is enrolled automatically the first time it is switched on.

This chapter is the one the DocBot prototype exercises. The console code behind
it is `src/enrollment/ios/**` — in this same repository, mapped to the area
`enrollment-ios` in `doc-map.json`. A merge request may change both, and that is
the outcome to aim for; DocBot exists for the merge requests that change only
the first.

## Prerequisites

- An Apple Business Manager account for the organisation.
- An MDM push certificate, uploaded under **Settings >> Apple >> Push
  certificate**. The certificate is valid for one year and must be renewed
  before it expires; a device does not re-enrol by itself after a lapse.
- The devices to be enrolled, already visible in Apple Business Manager.

## Connect MobiVisor to Apple Business Manager

**Settings >> Apple >> Business Manager** opens the connection interface.

1. Select *Download public key*. A `.pem` file is downloaded.
2. In Apple Business Manager, open **Preferences >> MDM Servers** and add a
   server. Upload the public key from step 1.
3. Download the server token from Apple Business Manager.
4. Return to MobiVisor and select *Upload token*, then select the downloaded
   token file.
5. Select *Save*.

The connection is listed with the expiry date of the token. The token is valid
for one year.

## Create an enrolment profile

**Enrollment >> Profiles >> Add** opens the enrolment wizard.

1. Enter a *Profile name*.
2. Select the *Platform* **iOS**.
3. Select whether enrolment is *Mandatory*. When enrolment is mandatory, the
   MDM profile cannot be removed from the device by its user.
4. Select the setup steps to be skipped during first start. Skipped steps are
   not shown to the user of the device.
5. Assign a *Policy* to be applied after enrolment.
6. Select *Save*.

![The enrollment wizard](../../images/_enrollment_wizard_1.png)

## Assign devices to the profile

**Enrollment >> Devices** lists the devices that Apple Business Manager has
assigned to MobiVisor. Select the devices, select *Assign profile*, and select
the profile created above.

A device that has already been set up must be erased before the assignment
takes effect. Assignment of a device that is in use is applied at the next
erase, not immediately.

## Verify the enrolment

Switch the device on and follow the setup assistant. The device appears under
**Devices** with the status *Enrolled* once the profile has been applied.
