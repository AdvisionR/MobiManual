const helper = require('../helper');

describe('devices page', function () {
  beforeEach(function () {
    browser.get('#!/devices');
  });

  it('should list enrolled devices', function () {
    expect(element.all(by.repeater('device in devices')).count()).toBeGreaterThan(0);
    helper.screenshot();
  });

  it('should hide retired devices while the enrolled filter is on', function () {
    element(by.model('filter.enrolled')).click();
    expect(element.all(by.cssContainingText('td', 'Retired')).count()).toBeGreaterThan(0);
    element(by.model('filter.enrolled')).click();
    expect(element.all(by.cssContainingText('td', 'Retired')).count()).toBe(0);
  });
});
