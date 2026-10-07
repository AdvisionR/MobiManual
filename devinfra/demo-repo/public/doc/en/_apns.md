# Access Point Names

Access Point Names (APNs) are the settings a device needs to use a carrier's
mobile data network. Carriers that run a private network for a company issue
their own APN. MobiVisor delivers APN entries to the devices of the groups they
are assigned to.

## Adding an APN

1. Open **Access Point Names** and select **Add**.
2. Enter a name for the entry and the APN the carrier gave you.
3. If the carrier requires it, enter the username and the password, and choose
   the authentication type: **None**, **PAP** or **CHAP**.
4. Choose the groups.
5. Select **Save**.

![](screenshots/_apn_add_form_1.png)

Devices receive the entry at their next check-in. Changing an entry replaces it
on every device in its groups; a device can lose mobile data briefly while it
switches.
