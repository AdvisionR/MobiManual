// Commands are queued on the server (server/commands/command-queue.js) and
// delivered at the device's next check-in. Which commands a device supports,
// and who may send them, comes from server/commands/definitions.js.

angular.module('mobivisor').factory('commandService', ['api', function (api) {
  return {
    definitions: function () { return api.get('/commands/definitions'); },
    history: function (deviceId) { return api.get('/devices/' + deviceId + '/commands'); },
    send: function (deviceIds, command, confirmation) {
      return api.post('/commands', { devices: deviceIds, command: command, confirmation: confirmation });
    },
    retry: function (commandId) { return api.post('/commands/' + commandId + '/retry'); }
  };
}]);
