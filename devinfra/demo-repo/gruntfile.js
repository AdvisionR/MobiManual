// Documentation build.
//
// htmlDocPages is the order of the manual. A Markdown file that is not listed
// here exists on disk but appears in neither combined.html nor the PDF, so
// adding a page is two steps, not one.
//
// search.md and break.md are not listed: the build injects search.md into
// combined.html and break.md between pages when producing the PDF.

var htmlDocPages = [
  'cover_page.md',
  'chapter1.md',
  '_users.md',
  '_devices.md',
  '_devices_id.md',
  '_enrollment_ios.md',
  '_policies_kiosk.md',
  '_policies_restrictions.md'
];

var languages = ['en', 'tr', 'de'];

module.exports = function (grunt) {
  grunt.initConfig({
    htmlDocPages: htmlDocPages,
    languages: languages
  });

  // Markdown -> index.html, combined.html and mobivisor.pdf, from the same
  // ordered page list.
  grunt.registerTask('web_docs', 'Generate HTML and PDF documentation', function () {
    grunt.log.writeln('pandoc: ' + htmlDocPages.length + ' pages x ' + languages.length + ' languages');
  });

  // Recapture screenshots for one language. Requires a running console and the
  // Protractor suite; not available in this fixture.
  languages.forEach(function (lang) {
    grunt.registerTask('screenshot_' + lang, 'Recapture ' + lang + ' screenshots', function () {
      grunt.fail.warn('screenshot runs need a browser and the E2E stack');
    });
  });

  grunt.registerTask('check-missing-doc', 'Check documentation completeness', function () {
    var done = this.async();
    grunt.util.spawn({ cmd: 'node', args: ['scripts/check-missing-doc.js'], opts: { stdio: 'inherit' } },
      function (error) { done(!error); });
  });
};
