// New local users, and users whose password is reset, get an email with a link
// to set a password. The link works once.

const crypto = require('crypto');

const LINK_VALID_HOURS = 48;

function issue(user, now) {
  return {
    user: user.id,
    token: crypto.randomBytes(32).toString('hex'),
    expires: new Date(now.getTime() + LINK_VALID_HOURS * 60 * 60 * 1000)
  };
}

module.exports = { issue, LINK_VALID_HOURS };
