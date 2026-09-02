// Protractor configuration for screenshot runs.
//
// protractor-screenshot-reporter writes into the same directory as helper.js
// but names files after Jasmine descriptions rather than routes. The two
// mechanisms are independent; do not assume one naming rule covers both.

const ScreenshotReporter = require('protractor-screenshot-reporter');

const LANGUAGE = process.env.SCREENSHOT_LANGUAGE || 'en';

exports.config = {
  framework: 'jasmine',
  specs: ['specs/*.spec.js'],
  baseUrl: 'http://localhost:9000',

  onPrepare: function () {
    jasmine.getEnv().addReporter(new ScreenshotReporter({
      baseDirectory: 'public/doc/' + LANGUAGE + '/screenshots'
    }));
  }
};
