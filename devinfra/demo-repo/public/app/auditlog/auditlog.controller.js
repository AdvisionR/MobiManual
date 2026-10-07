angular.module('mobivisor').controller('AuditLogCtrl', ['$scope', 'api', function ($scope, api) {
  $scope.filter = { user: '', action: '', from: null, to: null };

  $scope.reload = function () {
    api.get('/audit', $scope.filter).then(function (entries) {
      $scope.entries = entries;
    });
  };

  $scope.exportCsv = function () {
    return api.get('/audit/export.csv', $scope.filter);
  };

  $scope.reload();
}]);
