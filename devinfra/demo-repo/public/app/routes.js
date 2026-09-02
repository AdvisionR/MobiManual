// Route table for the MobiVisor console.
//
// Documentation filenames are derived from these paths: slashes become
// underscores and parameters collapse to "id", so #!/devices/:id is
// documented in _devices_id.md. scripts/check-missing-doc.js enforces it.

angular.module('mobivisor').config(['$routeProvider', function ($routeProvider) {
  $routeProvider
    .when('/users',                 { templateUrl: 'app/users/users.html',                          controller: 'UsersCtrl' })
    .when('/devices',               { templateUrl: 'app/devices/devices.html',                      controller: 'DevicesCtrl' })
    .when('/devices/:id',           { templateUrl: 'app/devices/device-detail.html',                controller: 'DeviceDetailCtrl' })
    .when('/enrollment/ios',        { templateUrl: 'app/enrollment/ios/enrollment-wizard.html',     controller: 'EnrollmentWizardCtrl' })
    .when('/policies/kiosk',        { templateUrl: 'app/policies/kiosk/kiosk.html',                 controller: 'KioskCtrl' })
    .when('/policies/restrictions', { templateUrl: 'app/policies/restrictions/restrictions.html',   controller: 'RestrictionsCtrl' })
    .when('/reports/export',        { templateUrl: 'app/reports/export-schedule.html',              controller: 'ExportScheduleCtrl' })
    .otherwise({ redirectTo: '/devices' });
}]);
