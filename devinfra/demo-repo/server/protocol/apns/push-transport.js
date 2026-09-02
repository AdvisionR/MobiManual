// APNs delivery. Internal plumbing with no user-visible surface.

const http2 = require('http2');

const ENDPOINT = 'https://api.push.apple.com';
const MAX_PAYLOAD_BYTES = 4096;

function send(token, payload) {
  if (Buffer.byteLength(JSON.stringify(payload)) > MAX_PAYLOAD_BYTES) {
    throw new Error('APNs payload exceeds ' + MAX_PAYLOAD_BYTES + ' bytes');
  }
  const session = http2.connect(ENDPOINT);
  return new Promise((resolve, reject) => {
    const req = session.request({ ':method': 'POST', ':path': '/3/device/' + token });
    req.on('response', (headers) => resolve(headers[':status']));
    req.on('error', reject);
    req.end(JSON.stringify(payload));
  });
}

module.exports = { send };
