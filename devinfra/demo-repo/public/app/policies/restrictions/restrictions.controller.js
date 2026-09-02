angular.module('mobivisor').controller('RestrictionsCtrl', ['$scope', 'schemaService', function ($scope, schemaService) {
  $scope.restrictions = schemaService.load('policies/android-restrictions.json');

  $scope.save = function () {
    return schemaService.save('android-restrictions', $scope.restrictions);
  };
}]);
