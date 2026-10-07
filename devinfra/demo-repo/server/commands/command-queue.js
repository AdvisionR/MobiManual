// Commands wait here until the device checks in and acknowledges them. One the
// device has not acknowledged in time is marked expired; the console can queue
// it again (Retry).

const EXPIRY_HOURS = 24;

function enqueue(db, deviceId, command, sentBy, now) {
  return db.commands.insert({
    device: deviceId,
    command: command,
    sentBy: sentBy,
    sentAt: now,
    expiresAt: new Date(now.getTime() + EXPIRY_HOURS * 60 * 60 * 1000),
    state: 'queued'
  });
}

function expire(db, now) {
  return db.commands.update({ state: 'queued', expiresAt: { $lt: now } }, { state: 'expired' });
}

function pendingFor(db, deviceId) {
  return db.commands.find({ device: deviceId, state: 'queued' });
}

module.exports = { enqueue, expire, pendingFor, EXPIRY_HOURS };
