# Benutzer

Die Seite Benutzer listet alle Konten auf, die sich an der Konsole anmelden
können, mit Anmeldename, E-Mail-Adresse, Rolle und Quelle. Die Quelle ist
**Lokal** für hier angelegte Konten und **LDAP** für Konten, die aus dem
Verzeichnis importiert wurden.

![](screenshots/users_page-should_list_accounts.png)

## Benutzer hinzufügen

1. Öffnen Sie **Benutzer** und wählen Sie **Hinzufügen**.
2. Geben Sie Anmeldename und E-Mail-Adresse ein.
3. Wählen Sie eine Rolle. Die Rolle bestimmt, welche Seiten der Benutzer
   öffnen darf.
4. Wählen Sie **Speichern**.

Der neue Benutzer erhält eine E-Mail mit einem Link, über den er ein Passwort
festlegt. Der Link kann einmal verwendet werden und ist 48 Stunden gültig.

## Rollen

| Rolle | Darf |
|---|---|
| Administrator | Alles, auch Einstellungen, Geräte außer Betrieb nehmen und löschen sowie das Audit-Protokoll |
| Helpdesk | Geräte, Gruppen, Richtlinien, Apps und Benutzer ansehen; Geräte zwischen Gruppen verschieben; die Abteilung eines Geräts setzen; **Sperren**, **Klingeln** und **Gerätecode entfernen** senden |
| Auditor | Geräte, Gruppen, Richtlinien, Apps und Benutzer ansehen und das Audit-Protokoll lesen |

Nur Administratoren können Benutzer hinzufügen oder die Rolle eines Benutzers
ändern.

## Import aus LDAP

Wählen Sie **Importieren**, um Konten aus dem konfigurierten Verzeichnis zu
lesen. Vorhandene Konten werden über den Anmeldenamen zugeordnet und nicht
doppelt angelegt. Importierte Konten erhalten die Rolle Auditor, bis ein
Administrator sie ändert.

Das Verzeichnis wird unter **Einstellungen > Verzeichnis** eingerichtet.

## Benutzer deaktivieren

Wählen Sie **Deaktivieren** neben einem Konto. Ein deaktivierter Benutzer kann
sich nicht mehr anmelden; die Geräte, die er registriert hat, bleiben verwaltet.
Mit **Aktivieren** kann er sich wieder anmelden.

## Passwort zurücksetzen

Wählen Sie **Passwort zurücksetzen** neben einem lokalen Konto. Der Benutzer
erhält eine E-Mail mit einem Link zum Festlegen eines neuen Passworts, der
48 Stunden gültig ist. Das neue Passwort muss mindestens 8 Zeichen lang sein und
einen Buchstaben und eine Ziffer enthalten.

Konten aus dem Verzeichnis ändern ihr Passwort im Verzeichnis.
