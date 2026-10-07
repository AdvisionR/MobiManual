angular.module('mobivisor').controller('EnrollmentWizardCtrl', ['$scope', 'depService', 'groupService', function ($scope, depService, groupService) {
  $scope.step = 1;
  $scope.profile = { supervised: true, mdmRemovable: false, group: null };

  groupService.list().then(function (groups) {
    $scope.groups = groups;
  });

  $scope.next = function () {
    $scope.step += 1;
  };

  $scope.finish = function () {
    return depService.assignProfile($scope.profile);
  };
}]);
