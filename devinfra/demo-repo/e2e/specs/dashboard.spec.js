const helper = require('../helper');

describe('dashboard', function () {
  it('should show the four tiles', function () {
    browser.get('#!/dashboard');
    expect(element.all(by.css('.tile')).count()).toBe(4);
    helper.screenshot();
  });
});
