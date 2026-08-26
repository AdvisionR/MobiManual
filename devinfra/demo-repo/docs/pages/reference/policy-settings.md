---
title: Policy settings reference
class: generated
area: policy-schema
generated_from: schema/policies/**
generator: docbot render-reference
---

<!--
  DO NOT EDIT. class: generated — foundation doc §6.4.

  Everything below the marker is rendered from the policy schemas at build
  time. Hand edits are lost at the next build, and a model must never write
  here at all: this is reference data, and §6.4 puts it in the class with
  "no AI, no hallucination risk" precisely because it is the part a reader
  trusts literally.

  §3.2 measured exactly one table in the whole manual, which for an MDM product
  is surprising enough that §12 question #7 asks whether the reference tables
  exist anywhere at all. If they do not, this class is where they should be
  created — it is the highest-value, zero-risk part of the plan.

  The renderer does not exist yet: `docbot render-reference` is blocked on §12
  question #2 (are the schemas TypeScript or backend-side?). The table below is
  a hand-written sample of the shape it will produce, kept short on purpose so
  nobody mistakes it for real reference data.
-->

# Policy settings reference

<!-- BEGIN GENERATED: policy-settings -->

## Android Enterprise — device restrictions

| Setting | Key | Type | Default | Applies to |
|---|---|---|---|---|
| Allow camera | `camera_enabled` | boolean | `true` | Fully managed, Work profile |
| Allow screen capture | `screen_capture_enabled` | boolean | `true` | Fully managed |
| Allow USB file transfer | `usb_file_transfer_enabled` | boolean | `false` | Fully managed |
| Minimum passcode length | `passcode_minimum_length` | integer | `6` | Fully managed, Work profile |

## iOS — device restrictions

| Setting | Key | Type | Default | Applies to |
|---|---|---|---|---|
| Allow app installation | `allowAppInstallation` | boolean | `true` | Supervised |
| Allow erase all content | `allowEraseContentAndSettings` | boolean | `true` | Supervised |
| Force encrypted backup | `forceEncryptedBackup` | boolean | `false` | All |

<!-- END GENERATED: policy-settings -->
