angular.module('mobivisor').factory('deviceService', ['api', function (api) {
  return {
    // filter: { platform: 'all' | 'android' | 'ios', enrolled: boolean, search: string }
    list: function (filter) { return api.get('/devices', filter); },
    get: function (id) { return api.get('/devices/' + id); },
    moveToGroup: function (ids, groupId) { return api.post('/devices/move', { ids: ids, group: groupId }); },
    setDepartment: function (id, departmentId) { return api.put('/devices/' + id + '/department', { department: departmentId }); },
    exportCsv: function (filter) { return api.get('/devices/export.csv', filter); }
  };
}]);
