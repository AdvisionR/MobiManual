angular.module('mobivisor').controller('EnrollmentWizardCtrl', ['$scope', 'depService', function ($scope, depService) {
  $scope.step = 1;
  $scope.profile = { supervised: true, mdmRemovable: false };

  $scope.next = function () {
    $scope.step += 1;
  };

  $scope.finish = function () {
    return depService.assignProfile($scope.profile);
  };
}]);
