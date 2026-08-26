---
title: Users
class: ai-drafted
area: users-and-roles
---

# Users

The *Users* area lists the administrator accounts of the tenant and the end
users to whom devices are assigned. It is reached from the main menu.

## Add a user

**Users >> Add** opens the interface for adding a new user.

1. Enter the *User name*. The user name must be unique within the tenant.
2. Enter the *E-mail address*. Invitation and password reset messages are sent
   to this address.
3. Select a *Role*. The role determines what the user is permitted to do in the
   console; see **Roles**.
4. Optionally assign the user to a *Group*. Policies assigned to a group apply
   to every user in it.
5. Select *Save*.

The new user receives an invitation message at the address entered in step 2.
Until the invitation is accepted, the user is listed with the status *Pending*.

![The add user form](../images/_users_add_1.png)

## Import users from a directory

Users can be imported from a directory service instead of being added one by
one. The connection to the directory is configured under
**Settings >> LDAP**.

**Users >> Import** opens the import interface.

1. Select the configured directory from the list.
2. Enter the search base, or select a saved one.
3. Select *Search*. The users found are listed with their directory attributes.
4. Select the users to be imported, and select a *Role* for them.
5. Select *Import*.

Imported users authenticate against the directory. Their password rules are the
ones the directory enforces, and the password settings of the console do not
apply to them.

## Edit a user

Select a user in the list to open the user details. The user name cannot be
changed after the user has been created; to change it, the user must be removed
and added again.

## Remove a user

Select a user in the list and select *Delete*. Devices assigned to the user are
not removed. They remain enrolled and must be reassigned or wiped separately.
