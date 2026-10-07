# Gerätecode-Richtlinie

Eine Gerätecode-Richtlinie legt die Regeln für den Code fest, mit dem ein Gerät
entsperrt wird. Sie gilt für den Gerätecode, nicht für Konsolenpasswörter.

| Einstellung | Werte | Standard |
|---|---|---|
| **Mindestlänge** | 4 bis 16 Zeichen | 6 |
| **Buchstaben und Ziffern erforderlich** | an oder aus | aus |
| **Maximales Alter (Tage)** | 0 bis 730; 0 bedeutet nie | 90 |
| **Fehlversuche bis zum Löschen** | 0 bis 20; 0 bedeutet nie | 10 |

Erreicht ein Gerätecode sein maximales Alter, fragt das Gerät beim nächsten
Entsperren nach einem neuen.

Nach der eingestellten Zahl von Fehlversuchen löscht sich das Gerät selbst. Das
kann nicht rückgängig gemacht werden.

Hat ein Benutzer seinen Gerätecode vergessen, senden Sie
**Gerätecode entfernen** über den Reiter **Befehle** des Geräts.
