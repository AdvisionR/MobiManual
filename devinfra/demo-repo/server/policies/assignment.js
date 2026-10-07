// A group holds at most one policy of each type: assigning a second one of the
// same type replaces the first. Devices receive the change at their next check-in.

function assign(group, policy) {
  const kept = group.policies.filter((p) => p.type !== policy.type);
  return { ...group, policies: [...kept, policy] };
}

module.exports = { assign };
