// Stand-in for the directory-service settings screen.
// Doc-map area: users-and-roles, class ai-drafted — it is documented in
// docs/pages/users.md ("Import users from a directory").

export function LdapSettings() {
  return { host: '', baseDn: '', bindUser: '', tls: true };
}
