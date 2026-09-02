angular.module('mobivisor').controller('UsersCtrl', ['$scope', 'userService', function ($scope, userService) {
  $scope.users = [];
  $scope.source = 'local';

  $scope.reload = function () {
    userService.list({ source: $scope.source }).then(function (users) {
      $scope.users = users;
    });
  };

  $scope.reload();
}]);
