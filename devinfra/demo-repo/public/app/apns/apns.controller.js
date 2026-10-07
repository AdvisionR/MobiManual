// Access Point Names: the cellular data settings a carrier gives out. Sent to
// devices as part of their configuration at the next check-in
// (server/policies/apn.js). Nothing to do with Apple Push (APNs).

angular.module('mobivisor').controller('ApnsCtrl', ['$scope', 'api', 'groupService', function ($scope, api, groupService) {
  $scope.authTypes = ['none', 'pap', 'chap'];

  $scope.reload = function () {
    api.get('/apns').then(function (apns) {
      $scope.apns = apns;
    });
  };

  groupService.list().then(function (groups) {
    $scope.groups = groups;
  });

  $scope.add = function () {
    $scope.draft = { authType: 'none', groups: [] };
  };

  $scope.save = function () {
    return api.post('/apns', $scope.draft).then(function () {
      $scope.draft = null;
      $scope.reload();
    });
  };

  $scope.reload();
}]);
