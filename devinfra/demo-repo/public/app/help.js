// The help link in the top bar opens the manual at the current page's section,
// in the console's language. The page name follows the rule in routes.js:
// #!/policies/kiosk -> doc/<lang>/_policies_kiosk.html.

angular.module('mobivisor').directive('helpLink', ['$location', '$translate', function ($location, $translate) {
  return {
    restrict: 'E',
    template: '<a ng-href="{{ href() }}" target="_blank">{{ \'NAV.HELP\' | translate }}</a>',
    link: function (scope) {
      scope.href = function () {
        var segments = $location.path().replace(/^\//, '').split('/').map(function (s) {
          return /^[0-9a-f-]{8,}$/.test(s) ? 'id' : s;
        });
        return 'doc/' + ($translate.use() || 'en') + '/_' + segments.join('_') + '.html';
      };
    }
  };
}]);
