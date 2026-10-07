angular.module('mobivisor').controller('ExportScheduleCtrl', ['$scope', 'reportService', function ($scope, reportService) {
  $scope.schedule = { interval: 'weekly', format: 'csv', recipients: [] };

  $scope.save = function () {
    return reportService.saveSchedule($scope.schedule);
  };
}]);
