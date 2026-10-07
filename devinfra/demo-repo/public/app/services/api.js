// Thin wrapper over $http for the console's REST API (server/api/).
// Every call resolves with the response body; a 401 sends the browser to the
// sign-in page, which is how an expired session ends.

angular.module('mobivisor').factory('api', ['$http', '$window', function ($http, $window) {
  function body(response) {
    return response.data;
  }

  function failed(response) {
    if (response.status === 401) {
      $window.location.href = '/login.html?reason=timeout';
    }
    throw response;
  }

  return {
    get: function (path, params) { return $http.get('/api' + path, { params: params }).then(body, failed); },
    post: function (path, data) { return $http.post('/api' + path, data).then(body, failed); },
    put: function (path, data) { return $http.put('/api' + path, data).then(body, failed); },
    remove: function (path) { return $http.delete('/api' + path).then(body, failed); }
  };
}]);
