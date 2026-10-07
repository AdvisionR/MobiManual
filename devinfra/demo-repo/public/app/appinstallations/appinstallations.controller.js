// Installs apps on the devices of the chosen groups. A failed installation is
// retried by the server (server/apps/install-retry.js); Retry here queues it
// again after that.

angular.module('mobivisor').controller('AppInstallationsCtrl', ['$scope', 'api', 'groupService', function ($scope, api, groupService) {
  $scope.reload = function () {
    api.get('/appinstallations').then(function (installations) {
      $scope.installations = installations;
    });
  };

  groupService.list().then(function (groups) {
    $scope.groups = groups;
  });

  $scope.search = function (term) {
    return api.get('/apps/search', { q: term }).then(function (apps) {
      $scope.found = apps;
    });
  };

  $scope.create = function (installation) {
    return api.post('/appinstallations', installation).then(function () {
      $scope.draft = null;
      $scope.reload();
    });
  };

  $scope.retry = function (installation, device) {
    return api.post('/appinstallations/' + installation.id + '/devices/' + device.id + '/retry').then($scope.reload);
  };

  $scope.remove = function (installation) {
    return api.remove('/appinstallations/' + installation.id).then($scope.reload);
  };

  $scope.reload();
}]);
