angular.module('mobivisor').controller('KioskCtrl', ['$scope', 'policyService', function ($scope, policyService) {
  $scope.mode = 'single-app';
  $scope.allowedApps = [];

  $scope.save = function () {
    return policyService.saveKiosk({ mode: $scope.mode, allowedApps: $scope.allowedApps });
  };
}]);
