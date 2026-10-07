// Route table for the MobiVisor console.
//
// Documentation filenames are derived from these paths: slashes become
// underscores and parameters collapse to "id", so #!/devices/:id is
// documented in _devices_id.md. scripts/check-missing-doc.js enforces it.

angular.module('mobivisor').config(['$routeProvider', function ($routeProvider) {
  $routeProvider
    .when('/dashboard',             { templateUrl: 'app/dashboard/dashboard.html',                  controller: 'DashboardCtrl' })
    .when('/users',                 { templateUrl: 'app/users/users.html',                          controller: 'UsersCtrl' })
    .when('/groups',                { templateUrl: 'app/groups/groups.html',                        controller: 'GroupsCtrl' })
    .when('/devices',               { templateUrl: 'app/devices/devices.html',                      controller: 'DevicesCtrl' })
    .when('/devices/:id',           { templateUrl: 'app/devices/device-detail.html',                controller: 'DeviceDetailCtrl' })
    .when('/devicescommands',       { templateUrl: 'app/devicescommands/devicescommands.html',      controller: 'DeviceCommandsCtrl' })
    .when('/enrollment/android',    { templateUrl: 'app/enrollment/android/android-enrollment.html', controller: 'AndroidEnrollmentCtrl' })
    .when('/enrollment/ios',        { templateUrl: 'app/enrollment/ios/enrollment-wizard.html',     controller: 'EnrollmentWizardCtrl' })
    .when('/policies',              { templateUrl: 'app/policies/policies.html',                    controller: 'PoliciesCtrl' })
    .when('/policies/passcode',     { templateUrl: 'app/policies/passcode/passcode.html',           controller: 'PasscodeCtrl' })
    .when('/policies/kiosk',        { templateUrl: 'app/policies/kiosk/kiosk.html',                 controller: 'KioskCtrl' })
    .when('/policies/restrictions', { templateUrl: 'app/policies/restrictions/restrictions.html',   controller: 'RestrictionsCtrl' })
    .when('/apns',                  { templateUrl: 'app/apns/apns.html',                            controller: 'ApnsCtrl' })
    .when('/appinstallations',      { templateUrl: 'app/appinstallations/appinstallations.html',    controller: 'AppInstallationsCtrl' })
    .when('/auditlog',              { templateUrl: 'app/auditlog/auditlog.html',                    controller: 'AuditLogCtrl' })
    .when('/settings',              { templateUrl: 'app/settings/settings.html',                    controller: 'SettingsCtrl' })
    .when('/reports/export',        { templateUrl: 'app/reports/export-schedule.html',              controller: 'ExportScheduleCtrl' })
    .otherwise({ redirectTo: '/dashboard' });
}]);
