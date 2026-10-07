// Departments come from the directory (Settings > Directory) and are attached
// to devices for reporting. They are not groups: policies follow groups.

angular.module('mobivisor').factory('departmentService', ['api', function (api) {
  return {
    list: function () { return api.get('/departments'); }
  };
}]);
