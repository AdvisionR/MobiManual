// Android enrollment: a QR code for fully managed devices, scanned during
// setup, or a token for work profiles, typed into the MobiVisor Agent app.
// Both are issued by server/enrollment/android-tokens.js, which sets how long
// they stay valid.

angular.module('mobivisor').controller('AndroidEnrollmentCtrl', ['$scope', 'api', 'groupService', function ($scope, api, groupService) {
  $scope.mode = 'fully-managed';

  groupService.list().then(function (groups) {
    $scope.groups = groups;
    $scope.group = groups.filter(function (g) { return g.isDefault; })[0];
  });

  $scope.create = function () {
    return api.post('/enrollment/android', { mode: $scope.mode, group: $scope.group.id }).then(function (issued) {
      $scope.issued = issued;
    });
  };
}]);
