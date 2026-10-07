const helper = require('../helper');

describe('app installations', function () {
  it('should list installations with their device status', function () {
    browser.get('#!/appinstallations');
    expect(element.all(by.repeater('installation in installations')).count()).toBeGreaterThan(0);
    helper.screenshot();
  });
});
