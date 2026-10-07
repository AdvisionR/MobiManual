// Adds the department reference to devices. Existing devices keep none until
// an administrator sets one.

exports.up = function (db) {
  return db.schema.alterTable('devices', function (table) {
    table.uuid('department_id').nullable().references('departments.id');
  });
};

exports.down = function (db) {
  return db.schema.alterTable('devices', function (table) {
    table.dropColumn('department_id');
  });
};
