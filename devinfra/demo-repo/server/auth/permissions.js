// What each console role may do. The API checks every request against this
// table; the console hides what a role cannot use.

const ROLES = {
  administrator: ['*'],
  helpdesk: [
    'devices.read', 'devices.move', 'devices.department',
    'commands.lock', 'commands.ring', 'commands.clear-passcode',
    'groups.read', 'policies.read', 'apps.read', 'users.read'
  ],
  auditor: [
    'devices.read', 'groups.read', 'policies.read', 'apps.read', 'users.read', 'audit.read'
  ]
};

function allowed(role, action) {
  const grants = ROLES[role] || [];
  return grants.includes('*') || grants.includes(action);
}

module.exports = { ROLES, allowed };
