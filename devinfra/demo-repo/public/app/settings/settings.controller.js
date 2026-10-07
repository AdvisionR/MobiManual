// Administrators only. Session timeout limits are enforced by server/auth/session.js.

angular.module('mobivisor').controller('SettingsCtrl', ['$scope', 'api', function ($scope, api) {
  api.get('/settings').then(function (settings) {
    $scope.settings = settings;
  });

  $scope.downloadCsr = function () {
    return api.get('/settings/push-certificate/csr');
  };

  $scope.uploadCertificate = function (file) {
    return api.post('/settings/push-certificate', file);
  };

  $scope.testDirectory = function () {
    return api.post('/settings/directory/test', $scope.settings.directory).then(function (result) {
      $scope.directoryResult = result;
    });
  };

  $scope.save = function (section) {
    return api.put('/settings/' + section, $scope.settings[section]);
  };
}]);
