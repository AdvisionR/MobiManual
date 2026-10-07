angular.module('mobivisor').factory('policyService', ['api', function (api) {
  return {
    list: function () { return api.get('/policies'); },
    save: function (policy) { return api.post('/policies', policy); },
    assign: function (policyId, groupIds) { return api.put('/policies/' + policyId + '/groups', { groups: groupIds }); },
    savePasscode: function (settings) { return api.post('/policies/passcode', settings); },
    saveKiosk: function (settings) { return api.post('/policies/kiosk', settings); }
  };
}]);
