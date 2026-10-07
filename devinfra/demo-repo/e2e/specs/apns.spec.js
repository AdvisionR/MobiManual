const helper = require('../helper');

describe('access point names', function () {
  it('should require a group for a new entry', function () {
    browser.get('#!/apns');
    element(by.css('[ng-click="add()"]')).click();
    element(by.model('draft.name')).sendKeys('Company LTE');
    element(by.model('draft.apn')).sendKeys('company.example');
    helper.docshot('apn_add_form');
    expect(element(by.css('form[name="apnForm"] button[type="submit"]')).isEnabled()).toBe(false);
  });
});
