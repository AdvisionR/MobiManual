describe('users page', function () {
  beforeEach(function () {
    browser.get('#!/users');
  });

  // The screenshot reporter names its capture after this description:
  // users_page-should_list_accounts.png.
  it('should list accounts', function () {
    expect(element.all(by.repeater('user in users')).count()).toBeGreaterThan(0);
  });

  it('should require a role before saving', function () {
    element(by.buttonText('Add')).click();
    element(by.model('draft.login')).sendKeys('e2e-user');
    element(by.model('draft.email')).sendKeys('e2e@example.invalid');
    expect(element(by.css('form[name="addUser"] button[type="submit"]')).isEnabled()).toBe(false);
  });
});
