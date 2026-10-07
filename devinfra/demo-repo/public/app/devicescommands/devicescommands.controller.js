// The command reference: every command, the platforms it runs on and the roles
// that may send it, as server/commands/definitions.js declares them.

angular.module('mobivisor').controller('DeviceCommandsCtrl', ['$scope', 'commandService', function ($scope, commandService) {
  commandService.definitions().then(function (definitions) {
    $scope.definitions = definitions;
  });
}]);
