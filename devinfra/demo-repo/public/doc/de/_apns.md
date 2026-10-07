# Zugangspunkte (APN)

Zugangspunkte (Access Point Names, APN) sind die Einstellungen, die ein Gerät
für das Mobilfunk-Datennetz eines Anbieters braucht. Anbieter, die für ein
Unternehmen ein privates Netz betreiben, vergeben einen eigenen APN. MobiVisor
liefert APN-Einträge an die Geräte der Gruppen, denen sie zugewiesen sind.

## APN hinzufügen

1. Öffnen Sie **Zugangspunkte (APN)** und wählen Sie **Hinzufügen**.
2. Geben Sie einen Namen für den Eintrag und den APN des Anbieters ein.
3. Wenn der Anbieter es verlangt, geben Sie Benutzername und Passwort ein und
   wählen den Authentifizierungstyp: **Keine**, **PAP** oder **CHAP**.
4. Wählen Sie die Gruppen.
5. Wählen Sie **Speichern**.

![](screenshots/_apn_add_form_1.png)

Die Geräte erhalten den Eintrag beim nächsten Check-in. Ein geänderter Eintrag
ersetzt den alten auf allen Geräten seiner Gruppen; beim Umschalten kann ein
Gerät kurz keine mobilen Daten haben.
