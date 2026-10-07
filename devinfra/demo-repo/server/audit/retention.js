// Audit log entries older than the retention period are deleted every night.

const RETENTION_DAYS = 365;

function purge(db, now) {
  const cutoff = new Date(now.getTime() - RETENTION_DAYS * 24 * 60 * 60 * 1000);
  return db.audit.remove({ time: { $lt: cutoff } });
}

module.exports = { purge, RETENTION_DAYS };
