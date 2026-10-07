// A failed app installation is retried automatically before it is left as
// failed for an administrator to retry by hand.

const MAX_RETRIES = 3;
const RETRY_INTERVAL_MINUTES = 60;

function nextAttempt(installation, now) {
  if (installation.attempts > MAX_RETRIES) return null;
  return new Date(now.getTime() + RETRY_INTERVAL_MINUTES * 60 * 1000);
}

module.exports = { nextAttempt, MAX_RETRIES, RETRY_INTERVAL_MINUTES };
