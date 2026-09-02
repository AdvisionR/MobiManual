angular.module('mobivisor').controller('DevicesCtrl', ['$scope', 'deviceService', function ($scope, deviceService) {
  $scope.devices = [];
  $scope.filter = { platform: 'all', enrolled: true };

  $scope.reload = function () {
    deviceService.list($scope.filter).then(function (devices) {
      $scope.devices = devices;
    });
  };

  $scope.reload();
}]);
