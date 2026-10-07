// Every command the console can send. platforms: where it runs. supervisedOnly:
// iOS devices must be supervised. The roles that may send each one come from
// auth/permissions.js.

const { ROLES } = require('../auth/permissions');

const COMMANDS = [
  { name: 'lock', label: 'COMMANDS.LOCK', platforms: ['android', 'ios'] },
  { name: 'ring', label: 'COMMANDS.RING', platforms: ['android'], durationSeconds: 120 },
  { name: 'clear-passcode', label: 'COMMANDS.CLEAR_PASSCODE', platforms: ['android', 'ios'], supervisedOnly: true },
  { name: 'update-os', label: 'COMMANDS.UPDATE_OS', platforms: ['ios'], supervisedOnly: true },
  { name: 'retire', label: 'COMMANDS.RETIRE', platforms: ['android', 'ios'] },
  { name: 'wipe', label: 'COMMANDS.WIPE', platforms: ['android', 'ios'], confirm: 'password' }
];

function rolesFor(command) {
  return Object.keys(ROLES).filter((role) =>
    ROLES[role].includes('*') || ROLES[role].includes('commands.' + command.name));
}

function definitions() {
  return COMMANDS.map((command) => ({ ...command, roles: rolesFor(command) }));
}

module.exports = { COMMANDS, definitions };
