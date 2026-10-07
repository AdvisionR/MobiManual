// Enrollment credentials for Android. A QR code (fully managed) can enroll any
// number of devices until it expires; a work-profile token enrolls one.

const crypto = require('crypto');

const VALID_DAYS = 7;

function issue(mode, groupId, now) {
  return {
    mode: mode,
    group: groupId,
    token: crypto.randomBytes(12).toString('base64url'),
    singleUse: mode === 'work-profile',
    validUntil: new Date(now.getTime() + VALID_DAYS * 24 * 60 * 60 * 1000)
  };
}

module.exports = { issue, VALID_DAYS };
