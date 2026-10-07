const helper = require('../helper');

describe('policies', function () {
  it('should offer both kiosk modes', function () {
    browser.get('#!/policies/kiosk');
    expect(element.all(by.model('mode')).count()).toBe(2);
    helper.docshot('kiosk_mode');
  });

  it('should reject a minimum passcode length below 4', function () {
    browser.get('#!/policies/passcode');
    element(by.model('policy.minLength')).clear().sendKeys('3');
    expect(element(by.model('policy.minLength')).getAttribute('class')).toMatch('ng-invalid');
  });
});
