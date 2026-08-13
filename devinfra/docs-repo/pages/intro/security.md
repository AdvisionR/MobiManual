---
title: Security and data handling
class: human-only
area: security-statements
---

# Security and data handling

<!--
  class: human-only — foundation doc §6.4.

  The drafting agent must never edit this file. The statements below are
  customer-facing and arguably contractual (§7, on why option D is rejected):
  a plausible-sounding rewording of a data-residency commitment is a legal
  problem, not a documentation one.

  §6.7 makes this a validation gate rather than an instruction: a proposal that
  touches a human-only page fails the build. `docbot gate` also refuses to emit
  a `draft` action for an area of this class, and there is a test for it.
-->

## Data residency

Device inventory data, policy assignments and audit records are stored in the
data centre selected for the tenant at the time of provisioning. The selection
is fixed for the lifetime of the tenant and is not changed by any setting in
the console.

## Administrator authentication

Access to the console requires an administrator account. Accounts may be held
locally or supplied from a directory service; see **Users** for the import
procedure. Password rules for local accounts are configured under
**Settings >> Password**.

## Audit records

Every administrative action performed in the console is recorded with the
account that performed it and the time at which it was performed. Audit records
cannot be edited or removed from the console.

## Device data

MobiVisor collects the device inventory required to apply and verify the
policies assigned to a device. What is collected depends on the platform and on
the enrolment type, and is listed in the reference chapter.
