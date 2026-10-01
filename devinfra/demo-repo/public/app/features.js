// Features that ship dark. A finished feature is merged behind its flag and
// stays off until it is released; templates check FEATURES.<name> with ng-if.
// Turning a flag on is the release. A flag is deleted, with its ng-if, once
// the feature has been on for a release.

angular.module('mobivisor')
  .constant('FEATURES', {
    accountExpiry: false
  })
  .run(['$rootScope', 'FEATURES', function ($rootScope, FEATURES) {
    $rootScope.FEATURES = FEATURES;
  }]);
