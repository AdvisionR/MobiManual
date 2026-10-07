// Validates a passcode policy: the passcode a device user sets to unlock the
// device. Console passwords are auth/password-policy.js.

const LIMITS = {
  minLength: { min: 4, max: 16, default: 6 },
  maxAgeDays: { min: 0, max: 730, default: 90 },
  maxFailedAttempts: { min: 0, max: 20, default: 10 }
};

function validate(policy) {
  return Object.keys(LIMITS).filter((key) => {
    const value = policy[key];
    return !Number.isInteger(value) || value < LIMITS[key].min || value > LIMITS[key].max;
  });
}

module.exports = { validate, LIMITS };
