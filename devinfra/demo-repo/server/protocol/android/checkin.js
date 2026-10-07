// Android devices poll for pending commands and configuration. iOS devices are
// woken by an APNs push instead (protocol/apns/).

const CHECKIN_INTERVAL_MINUTES = 15;

function schedule(device) {
  return { device: device.id, everyMinutes: CHECKIN_INTERVAL_MINUTES };
}

module.exports = { schedule, CHECKIN_INTERVAL_MINUTES };
