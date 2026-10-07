# Einstellungen

Die Einstellungen sind nur für Administratoren zugänglich.

## Apple-Push-Zertifikat

MobiVisor erreicht iOS-Geräte über den Push-Dienst von Apple, der ein von Apple
ausgestelltes Zertifikat braucht. Das Zertifikat ist ein Jahr gültig.

1. Wählen Sie **CSR herunterladen**.
2. Melden Sie sich mit der Apple-ID Ihres Unternehmens im Apple Push
   Certificates Portal an und laden Sie die CSR hoch.
3. Laden Sie das Zertifikat bei Apple herunter und wählen Sie
   **Zertifikat hochladen**.

![](img/apple_push_portal.png)

Erneuern Sie das Zertifikat vor dem Ablauf, mit derselben Apple-ID. Ein mit
einer anderen Apple-ID erstelltes Zertifikat erreicht die bereits registrierten
Geräte nicht, und sie müssten alle neu registriert werden. Das Dashboard warnt
30 Tage vor dem Ablaufdatum.

## Verzeichnis

Geben Sie **Server-URL**, **Basis-DN** und **Bind-Benutzer** Ihres
LDAP-Verzeichnisses ein und wählen Sie dann **Verbindung testen** und
**Speichern**. Das Verzeichnis wird von **Importieren** auf der Seite Benutzer
und für die Abteilungen der Geräte verwendet.

## E-Mail-Benachrichtigungen

Geben Sie **SMTP-Server** und **Absenderadresse** ein. MobiVisor sendet E-Mails
für neue Konten, zurückgesetzte Passwörter und die Warnung zum
Apple-Push-Zertifikat.

## Sicherheit

**Sitzungs-Timeout (Minuten)** legt fest, wie lange die Konsole ohne Aktivität
angemeldet bleibt: 5 bis 120 Minuten. Standard ist 30.
