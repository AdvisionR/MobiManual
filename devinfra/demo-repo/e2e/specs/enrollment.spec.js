const helper = require('../helper');

describe('android enrollment', function () {
  it('should create a QR code for fully managed devices', function () {
    browser.get('#!/enrollment/android');
    element(by.css('[ng-click="create()"]')).click();
    expect(element(by.css('img[ng-src]')).isPresent()).toBe(true);
    helper.docshot('android_qr_code');
  });
});
