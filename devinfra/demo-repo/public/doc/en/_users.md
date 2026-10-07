# Users

The Users page lists every account that can sign in to the console, with its
login name, email address, role and source. The source is **Local** for
accounts created here and **LDAP** for accounts imported from the directory.

![](screenshots/users_page-should_list_accounts.png)

## Adding a user

1. Open **Users** and select **Add**.
2. Enter the login name and the email address.
3. Choose a role. The role determines which pages the user can open.
4. Select **Save**.

The new user receives an email with a link to set a password. The link can be
used once and is valid for 48 hours.

## Roles

| Role | Can |
|---|---|
| Administrator | Everything, including Settings, retiring and wiping devices, and the Audit Log |
| Helpdesk | View devices, groups, policies, apps and users; move devices between groups; set a device's department; send **Lock**, **Ring** and **Clear passcode** |
| Auditor | View devices, groups, policies, apps and users, and read the Audit Log |

Only administrators can add users or change a user's role.

## Importing from LDAP

Select **Import** to read accounts from the configured directory. Existing
accounts are matched by login name and are not duplicated. Imported accounts
get the Auditor role until an administrator changes it.

The directory is configured under **Settings > Directory**.

## Disabling a user

Select **Disable** next to an account. A disabled user can no longer sign in,
and the devices they enrolled stay managed. Select **Enable** to let them sign
in again.

## Resetting a password

Select **Reset password** next to a local account. The user receives an email
with a link to set a new password, valid for 48 hours. The new password must
have at least 8 characters, including a letter and a digit.

Accounts from the directory change their password in the directory.
