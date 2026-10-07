angular.module('mobivisor').controller('DeviceDetailCtrl', ['$scope', '$routeParams', 'deviceService', 'commandService', 'departmentService', function ($scope, $routeParams, deviceService, commandService, departmentService) {
  $scope.tab = 'overview';

  $scope.load = function () {
    deviceService.get($routeParams.id).then(function (device) {
      $scope.device = device;
    });
    commandService.history($routeParams.id).then(function (commands) {
      $scope.commands = commands;
    });
  };

  commandService.definitions().then(function (definitions) {
    $scope.definitions = definitions;
  });

  departmentService.list().then(function (departments) {
    $scope.departments = departments;
  });

  $scope.supported = function (definition) {
    return $scope.device && definition.platforms.indexOf($scope.device.platform) >= 0 &&
      (!definition.supervisedOnly || $scope.device.supervised);
  };

  $scope.send = function (definition, confirmation) {
    return commandService.send([$scope.device.id], definition.name, confirmation).then($scope.load);
  };

  $scope.retry = function (command) {
    return commandService.retry(command.id).then($scope.load);
  };

  $scope.saveDepartment = function (department) {
    return deviceService.setDepartment($scope.device.id, department.id).then(function () {
      $scope.editingDepartment = false;
      $scope.load();
    });
  };

  $scope.load();
}]);
