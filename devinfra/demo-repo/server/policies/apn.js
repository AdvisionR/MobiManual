// Access Point Name entries, delivered with the device configuration of the
// groups they are assigned to. A changed entry replaces the old one on the device.

const AUTH_TYPES = ['none', 'pap', 'chap'];

function payload(entry) {
  return {
    name: entry.name,
    apn: entry.apn,
    username: entry.username || null,
    password: entry.password || null,
    authType: AUTH_TYPES.includes(entry.authType) ? entry.authType : 'none'
  };
}

module.exports = { payload, AUTH_TYPES };
