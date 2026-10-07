// Console sessions end after a period without requests. The timeout is a
// setting (Settings > Security); these are its default and its bounds.

const DEFAULT_IDLE_MINUTES = 30;
const MIN_IDLE_MINUTES = 5;
const MAX_IDLE_MINUTES = 120;

function idleMinutes(settings) {
  const value = settings.security && settings.security.sessionTimeoutMinutes;
  if (!Number.isInteger(value)) return DEFAULT_IDLE_MINUTES;
  return Math.min(MAX_IDLE_MINUTES, Math.max(MIN_IDLE_MINUTES, value));
}

function expired(session, settings, now) {
  return now - session.lastSeen > idleMinutes(settings) * 60 * 1000;
}

module.exports = { idleMinutes, expired, DEFAULT_IDLE_MINUTES, MIN_IDLE_MINUTES, MAX_IDLE_MINUTES };
