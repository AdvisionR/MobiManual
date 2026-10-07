# Settings

Settings are open to administrators only.

## Apple Push certificate

MobiVisor reaches iOS devices through Apple's push service, which needs a
certificate issued by Apple. The certificate is valid for one year.

1. Select **Download CSR**.
2. Sign in to the Apple Push Certificates Portal with your company Apple ID and
   upload the CSR.
3. Download the certificate from Apple and select **Upload certificate**.

![](img/apple_push_portal.png)

Renew the certificate before it expires, with the same Apple ID. A certificate
created with another Apple ID cannot reach the devices already enrolled, and
they would all have to be enrolled again. The Dashboard warns 30 days before the
expiry date.

## Directory

Enter the **Server URL**, the **Base DN** and the **Bind user** of your LDAP
directory, then select **Test connection** and **Save**. The directory is used
by **Import** on the Users page and for device departments.

## Email notifications

Enter the **SMTP server** and the **Sender address**. MobiVisor sends email for
new accounts, password resets, and the Apple Push certificate warning.

## Security

**Session timeout (minutes)** sets how long the console stays signed in without
activity: from 5 to 120 minutes. The default is 30.
