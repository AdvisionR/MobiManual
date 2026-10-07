// All policies of every type. A group holds at most one policy per type, so
// assigning a second one of the same type to a group replaces the first
// (server/policies/assignment.js).

angular.module('mobivisor').controller('PoliciesCtrl', ['$scope', '$location', 'policyService', 'groupService', function ($scope, $location, policyService, groupService) {
  $scope.types = ['passcode', 'kiosk', 'restrictions'];

  $scope.reload = function () {
    policyService.list().then(function (policies) {
      $scope.policies = policies;
    });
  };

  groupService.list().then(function (groups) {
    $scope.groups = groups;
  });

  // A new policy is edited on its type's page.
  $scope.create = function (type) {
    $location.path('/policies/' + type);
  };

  $scope.assign = function (policy, groups) {
    return policyService.assign(policy.id, groups.map(function (g) { return g.id; })).then($scope.reload);
  };

  $scope.reload();
}]);
