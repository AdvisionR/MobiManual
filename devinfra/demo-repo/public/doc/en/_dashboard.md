# Dashboard

The dashboard is the first page after signing in. It shows four tiles, and
selecting a tile opens the page behind it.

![](screenshots/_dashboard_1.png)

| Tile | Shows | Opens |
|---|---|---|
| **Devices** | Enrolled devices, by platform | Devices |
| **Compliance** | The share of enrolled devices that are compliant | Devices |
| **Pending commands** | Commands that devices have not acknowledged yet | Devices |
| **Apple Push certificate** | Days until the certificate expires | Settings |

Retired and wiped devices are not counted on any tile.

The **Apple Push certificate** tile turns red 30 days before the certificate
expires. Renew it in time: see Settings.

The figures refresh every 5 minutes while the page is open.
