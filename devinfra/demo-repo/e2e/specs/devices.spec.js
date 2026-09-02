const helper = require('../helper');

describe('devices page', function () {
  beforeEach(function () {
    browser.get('#!/devices');
  });

  it('should list enrolled devices', function () {
    expect(element.all(by.repeater('device in devices')).count()).toBeGreaterThan(0);
    helper.screenshot();
  });

  it('should open the kiosk policy form', function () {
    element(by.css('[ng-click="openKiosk()"]')).click();
    helper.docshot('kiosk_mode');
  });
});
