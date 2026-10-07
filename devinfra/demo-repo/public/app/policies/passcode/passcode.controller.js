// Defaults and limits match server/policies/passcode.js, which validates them.

angular.module('mobivisor').controller('PasscodeCtrl', ['$scope', 'policyService', function ($scope, policyService) {
  $scope.policy = {
    name: '',
    minLength: 6,
    requireAlphanumeric: false,
    maxAgeDays: 90,
    maxFailedAttempts: 10
  };

  $scope.save = function () {
    return policyService.savePasscode($scope.policy);
  };
}]);
