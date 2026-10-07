angular.module('mobivisor').controller('UsersCtrl', ['$scope', 'userService', function ($scope, userService) {
  $scope.users = [];
  $scope.source = 'local';

  $scope.reload = function () {
    userService.list({ source: $scope.source }).then(function (users) {
      $scope.users = users;
    });
  };

  userService.roles().then(function (roles) {
    $scope.roles = roles;
  });

  $scope.save = function (draft) {
    return userService.save(draft).then(function () {
      $scope.adding = false;
      $scope.reload();
    });
  };

  $scope.toggleEnabled = function (user) {
    return userService.setEnabled(user.id, !user.enabled).then($scope.reload);
  };

  $scope.resetPassword = function (user) {
    return userService.resetPassword(user.id);
  };

  $scope.runImport = function () {
    return userService.importFromDirectory().then($scope.reload);
  };

  $scope.reload();
}]);
