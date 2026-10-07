angular.module('mobivisor').controller('DevicesCtrl', ['$scope', 'deviceService', 'groupService', 'commandService', function ($scope, deviceService, groupService, commandService) {
  $scope.devices = [];
  $scope.filter = { platform: 'all', enrolled: true };
  $scope.selected = {};

  $scope.reload = function () {
    deviceService.list($scope.filter).then(function (devices) {
      $scope.devices = devices;
      $scope.selected = {};
    });
  };

  groupService.list().then(function (groups) {
    $scope.groups = groups;
  });

  function selectedIds() {
    return Object.keys($scope.selected).filter(function (id) { return $scope.selected[id]; });
  }

  $scope.moveToGroup = function (group) {
    return deviceService.moveToGroup(selectedIds(), group.id).then($scope.reload);
  };

  $scope.send = function (command) {
    return commandService.send(selectedIds(), command).then($scope.reload);
  };

  $scope.exportCsv = function () {
    return deviceService.exportCsv($scope.filter);
  };

  $scope.reload();
}]);
