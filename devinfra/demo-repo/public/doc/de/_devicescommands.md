# Gerätebefehle

Befehle wirken aus der Ferne auf ein Gerät. Sie werden über den Reiter
**Befehle** eines Geräts gesendet oder aus der Geräteliste an mehrere Geräte
gleichzeitig. Diese Seite listet alle Befehle auf, wo sie laufen und wer sie
senden darf.

| Befehl | Android | iOS | Wer darf ihn senden |
|---|---|---|---|
| **Sperren** | ja | ja | Administrator, Helpdesk |
| **Klingeln** | ja | nein | Administrator, Helpdesk |
| **Gerätecode entfernen** | ja | nur überwacht | Administrator, Helpdesk |
| **Betriebssystem aktualisieren** | nein | nur überwacht | Administrator |
| **Außer Betrieb nehmen** | ja | ja | Administrator |
| **Vollständig löschen** | ja | ja | Administrator |

## Was die Befehle tun

- **Sperren** sperrt den Bildschirm. Der Benutzer entsperrt mit dem Gerätecode.
- **Klingeln** spielt 2 Minuten lang einen Ton ab, auch wenn das Gerät stumm
  geschaltet ist.
- **Gerätecode entfernen** entfernt den Gerätecode, damit der Benutzer einen
  neuen festlegen kann. Eine Gerätecode-Richtlinie verlangt beim nächsten
  Entsperren trotzdem einen.
- **Betriebssystem aktualisieren** installiert das iOS-Update, das das Gerät
  heruntergeladen hat.
- **Außer Betrieb nehmen** entfernt das Verwaltungsprofil, die Richtlinien und
  die Apps, die MobiVisor installiert hat. Persönliche Daten bleiben auf dem
  Gerät.
- **Vollständig löschen** löscht das Gerät und stellt die Werkseinstellungen
  wieder her. Bevor der Befehl in die Warteschlange kommt, fragt die Konsole
  nach Ihrem Passwort. Das Löschen kann nicht rückgängig gemacht werden.

## Zustellung

Ein Befehl wartet in einer Warteschlange, bis das Gerät sich meldet.
Android-Geräte melden sich alle 15 Minuten. iOS-Geräte werden durch eine
Push-Benachrichtigung geweckt, die ein gültiges Apple-Push-Zertifikat braucht
(siehe Einstellungen).

Ein Befehl, den das Gerät nicht innerhalb von 24 Stunden bestätigt, läuft ab.
Abgelaufene Befehle lassen sich mit **Erneut versuchen** auf dem Reiter
**Befehle** des Geräts erneut senden.
