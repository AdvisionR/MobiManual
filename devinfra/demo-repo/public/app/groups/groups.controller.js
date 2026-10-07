angular.module('mobivisor').controller('GroupsCtrl', ['$scope', 'groupService', 'policyService', function ($scope, groupService, policyService) {
  $scope.groups = [];

  $scope.reload = function () {
    groupService.list().then(function (groups) {
      $scope.groups = groups;
    });
  };

  policyService.list().then(function (policies) {
    $scope.policies = policies;
  });

  $scope.save = function (group) {
    return groupService.save(group).then(function () {
      $scope.editing = null;
      $scope.reload();
    });
  };

  // The server refuses to delete a group that still has devices, and the
  // Default group; the button is only offered for empty groups.
  $scope.canDelete = function (group) {
    return !group.isDefault && group.deviceCount === 0;
  };

  $scope.remove = function (group) {
    return groupService.remove(group.id).then($scope.reload);
  };

  $scope.assign = function (group, policy) {
    return groupService.assignPolicy(group.id, policy.id).then($scope.reload);
  };

  $scope.reload();
}]);
