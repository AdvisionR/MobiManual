// Builds the device list query behind GET /api/devices.

function where(filter) {
  const clause = {};
  if (filter.platform && filter.platform !== 'all') {
    clause.platform = filter.platform;
  }
  if (filter.enrolled) {
    clause.status = { $nin: ['wiped', 'retired'] };
  }
  if (filter.search) {
    const pattern = new RegExp(filter.search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
    clause.$or = [{ name: pattern }, { serial: pattern }, { owner: pattern }];
  }
  return clause;
}

module.exports = { where };
