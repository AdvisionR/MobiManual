angular.module('mobivisor').factory('reportService', ['api', function (api) {
  return {
    saveSchedule: function (schedule) { return api.put('/reports/export-schedule', schedule); }
  };
}]);
