angular.module('mobivisor').controller('RestrictionsCtrl', ['$scope', 'schemaService', function ($scope, schemaService) {
  schemaService.load('policies/android-restrictions.json').then(function (schema) {
    $scope.schema = schema;
    $scope.values = {};
    schema.settings.forEach(function (setting) {
      $scope.values[setting.key] = setting.default;
    });
  });

  $scope.save = function () {
    return schemaService.save('android-restrictions', $scope.values);
  };
}]);
