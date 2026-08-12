// Stand-in for internal push plumbing.
// Exists so a merge request can touch a path the doc map classifies as
// `no-doc-impact` (area: push-transport) — the case where the gate must stay
// silent. Proving silence is as important as proving detection.

export function sendPush(deviceToken: string, payload: object) {
  return { deviceToken, payload, transport: 'apns' };
}
