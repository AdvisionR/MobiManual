// Loads a policy schema from schema/policies/ and saves the values set for it.

angular.module('mobivisor').factory('schemaService', ['api', function (api) {
  return {
    load: function (file) { return api.get('/schema/' + file); },
    save: function (name, values) { return api.put('/policies/' + name, values); }
  };
}]);
