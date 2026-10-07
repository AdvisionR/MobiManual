// Apple Business Manager (formerly DEP): assigns the enrollment profile to the
// devices ABM has assigned to this server.

angular.module('mobivisor').factory('depService', ['api', function (api) {
  return {
    assignProfile: function (profile) { return api.post('/enrollment/ios/profile', profile); }
  };
}]);
