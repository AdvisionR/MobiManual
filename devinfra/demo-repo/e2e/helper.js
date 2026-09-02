// Screenshot helpers for the Protractor suite.
//
// Captures land in public/doc/<language>/screenshots/, where the manual
// references them. The language comes from SCREENSHOT_LANGUAGE.
//
// Filenames are the contract with the documentation: an explicit name is
// prefixed with an underscore, an omitted one is derived from the current
// route. Both gain a numeric index. Renaming a capture breaks the Markdown
// that references it.

const fs = require('fs');
const path = require('path');

const LANGUAGE = process.env.SCREENSHOT_LANGUAGE || 'en';
const OUT_DIR = path.join('public', 'doc', LANGUAGE, 'screenshots');

const counters = {};

function nextIndex(base) {
  counters[base] = (counters[base] || 0) + 1;
  return counters[base];
}

function baseNameFromUrl(url) {
  const route = url.split('#!')[1] || '/';
  return '_' + route.replace(/^\//, '').replace(/\//g, '_');
}

// Captures whenever it runs. Use when the screenshot is also useful as test
// evidence.
function screenshot(fileName) {
  return browser.getCurrentUrl().then(function (url) {
    const base = fileName ? '_' + fileName : baseNameFromUrl(url);
    const target = path.join(OUT_DIR, base + '_' + nextIndex(base) + '.png');
    return browser.takeScreenshot().then(function (png) {
      fs.mkdirSync(OUT_DIR, { recursive: true });
      fs.writeFileSync(target, png, 'base64');
      return target;
    });
  });
}

// Captures only during a screenshot run. Use for images the manual needs but
// the test itself does not.
function docshot(fileName) {
  if (process.env.NODE_ENV !== 'screenshot') {
    return Promise.resolve(null);
  }
  return screenshot(fileName);
}

module.exports = { screenshot, docshot, LANGUAGE, OUT_DIR };
