---
title: Roles
class: ai-drafted
area: users-and-roles
---

# Roles

A role is a named set of permissions. Every user has exactly one role, and the
role decides which areas of the console the user can open and which actions the
user can perform in them.

A newly provisioned tenant contains one role, *Administrator*, which holds all
permissions and cannot be removed.

## Add a role

**Roles >> Add** opens the interface for adding a new role.

1. Enter the *Role name*.
2. Enter a *Description*. The description is shown in the role list and helps
   to distinguish roles with similar permissions.
3. Select the permissions for the role. Permissions are grouped by console
   area; selecting the group heading selects every permission in the group.
4. Select *Save*.

## Edit a role

Select a role in the list to open its permissions, change the selection, and
select *Save*.

A change to a role takes effect the next time a user holding that role signs
in. A user who is signed in while the role is changed keeps the previous
permissions until the session ends.

## Remove a role

A role can only be removed when no user holds it. Reassign the affected users
first; the role list shows how many users hold each role.
