angular.module('mobivisor').controller('KioskCtrl', ['$scope', 'policyService', function ($scope, policyService) {
  $scope.mode = 'single-app';
  $scope.allowedApps = [];

  $scope.addApp = function (app) {
    if ($scope.mode === 'single-app') {
      $scope.allowedApps = [app];
    } else {
      $scope.allowedApps.push(app);
    }
  };

  $scope.save = function () {
    return policyService.saveKiosk({ mode: $scope.mode, allowedApps: $scope.allowedApps });
  };
}]);
