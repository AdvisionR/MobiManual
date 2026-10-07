// Kiosk policies. multi-app needs Android; single-app on iOS needs a
// supervised device. Leaving kiosk mode on the device takes the device passcode.

const MODES = ['single-app', 'multi-app'];

function supports(policy, device) {
  if (policy.mode === 'multi-app') return device.platform === 'android';
  return device.platform === 'android' || device.supervised;
}

module.exports = { MODES, supports };
