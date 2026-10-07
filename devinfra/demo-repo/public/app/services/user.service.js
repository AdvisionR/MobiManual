angular.module('mobivisor').factory('userService', ['api', function (api) {
  return {
    list: function (query) { return api.get('/users', query); },
    roles: function () { return api.get('/users/roles'); },
    save: function (user) { return api.post('/users', user); },
    setEnabled: function (id, enabled) { return api.put('/users/' + id + '/enabled', { enabled: enabled }); },
    resetPassword: function (id) { return api.post('/users/' + id + '/password-reset'); },
    importFromDirectory: function () { return api.post('/users/import'); }
  };
}]);
