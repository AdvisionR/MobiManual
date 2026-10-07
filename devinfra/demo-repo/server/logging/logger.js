// Structured logging for the API and the protocol handlers. One JSON object per
// line on stdout; the deployment ships it to the log store.

const LEVELS = ['debug', 'info', 'warn', 'error'];
const threshold = LEVELS.indexOf(process.env.LOG_LEVEL || 'info');

function log(level, message, fields) {
  if (LEVELS.indexOf(level) < threshold) return;
  process.stdout.write(JSON.stringify({ time: new Date().toISOString(), level, message, ...fields }) + '\n');
}

module.exports = Object.fromEntries(LEVELS.map((level) => [level, (message, fields) => log(level, message, fields)]));
