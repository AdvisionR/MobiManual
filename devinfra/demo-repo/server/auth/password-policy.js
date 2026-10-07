// Rules for console passwords (not device passcodes: see policies/passcode.js).
// Checked when a password is set, and on sign-in for the lockout.

const MIN_LENGTH = 8;
const REQUIRE_LETTER = true;
const REQUIRE_DIGIT = true;

// Failed sign-ins before the account is locked, and for how long.
const LOCKOUT_ATTEMPTS = 5;
const LOCKOUT_MINUTES = 15;

function check(password) {
  const problems = [];
  if (password.length < MIN_LENGTH) problems.push('min-length');
  if (REQUIRE_LETTER && !/[A-Za-z]/.test(password)) problems.push('letter');
  if (REQUIRE_DIGIT && !/[0-9]/.test(password)) problems.push('digit');
  return problems;
}

function lockedUntil(failures, lastFailure) {
  if (failures < LOCKOUT_ATTEMPTS) return null;
  return new Date(lastFailure.getTime() + LOCKOUT_MINUTES * 60 * 1000);
}

module.exports = { check, lockedUntil, MIN_LENGTH, LOCKOUT_ATTEMPTS, LOCKOUT_MINUTES };
