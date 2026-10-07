angular.module('mobivisor').factory('groupService', ['api', function (api) {
  return {
    list: function () { return api.get('/groups'); },
    save: function (group) { return group.id ? api.put('/groups/' + group.id, group) : api.post('/groups', group); },
    remove: function (id) { return api.remove('/groups/' + id); },
    assignPolicy: function (groupId, policyId) { return api.post('/groups/' + groupId + '/policies', { policy: policyId }); }
  };
}]);
