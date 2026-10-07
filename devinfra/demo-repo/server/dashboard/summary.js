// The numbers behind the dashboard tiles, computed on each request.

const PUSH_CERT_WARNING_DAYS = 30;

function summary(db, settings, now) {
  const counted = db.devices.find({ status: { $ne: 'wiped' } });
  const enrolled = counted.filter((d) => d.status === 'enrolled');
  const daysLeft = Math.floor((settings.pushCertificate.expires - now) / (24 * 60 * 60 * 1000));
  return {
    devices: {
      android: counted.filter((d) => d.platform === 'android').length,
      ios: counted.filter((d) => d.platform === 'ios').length
    },
    compliance: {
      percent: enrolled.length ? Math.round(100 * enrolled.filter((d) => d.compliant).length / enrolled.length) : 100
    },
    pendingCommands: db.commands.count({ state: 'queued' }),
    pushCertificate: { daysLeft: daysLeft, warning: daysLeft <= PUSH_CERT_WARNING_DAYS }
  };
}

module.exports = { summary, PUSH_CERT_WARNING_DAYS };
