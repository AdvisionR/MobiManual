// The console module. Labels come from public/i18n/<lang>.json through
// angular-translate: templates never contain English text, only keys.

angular.module('mobivisor', ['ngRoute', 'pascalprecht.translate'])
  .config(['$translateProvider', function ($translateProvider) {
    $translateProvider
      .useStaticFilesLoader({ prefix: 'i18n/', suffix: '.json' })
      .registerAvailableLanguageKeys(['en', 'tr', 'de'])
      .determinePreferredLanguage()
      .fallbackLanguage('en')
      .useSanitizeValueStrategy('escape');
  }])
  .run(['$rootScope', '$translate', 'api', function ($rootScope, $translate, api) {
    $rootScope.language = $translate.use() || 'en';
    $rootScope.useLanguage = function (language) {
      $translate.use(language);
      api.put('/me/language', { language: language });
    };
    api.get('/me').then(function (me) {
      $rootScope.session = me;
    });
  }]);
