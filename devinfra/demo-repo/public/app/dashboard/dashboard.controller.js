// The landing page after sign-in. Counts come from /api/dashboard, which
// leaves retired and wiped devices out of every number.

angular.module('mobivisor').controller('DashboardCtrl', ['$scope', '$interval', 'api', function ($scope, $interval, api) {
  var REFRESH_SECONDS = 300;

  $scope.load = function () {
    api.get('/dashboard').then(function (summary) {
      $scope.summary = summary;
      $scope.pushCertWarning = summary.pushCertificate.daysLeft <= 30;
    });
  };

  $scope.load();
  var timer = $interval($scope.load, REFRESH_SECONDS * 1000);
  $scope.$on('$destroy', function () { $interval.cancel(timer); });
}]);
