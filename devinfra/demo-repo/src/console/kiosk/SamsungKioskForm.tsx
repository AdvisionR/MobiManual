// Stand-in for the kiosk policy form.
// Doc-map area: kiosk-modes, class ai-drafted.
// Also the component behind the hand-captured screenshot registered in
// docs/images/registry.yaml — a change here is the case where the gate should
// flag the page *and* the screenshot.

export function SamsungKioskForm() {
  return { mode: 'multi-app', allowedApps: [] as string[], statusBar: 'hidden' };
}
