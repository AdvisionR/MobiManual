#!/usr/bin/env node
// Documentation completeness check.
//
//   1. every console route has a documentation page
//   2. every page is registered in htmlDocPages, and every entry has a file
//   3. every page exists in all languages
//
// search.md and break.md are build machinery and are excluded throughout.

'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const DOC_ROOT = path.join(ROOT, 'public', 'doc');
const SPECIAL = ['search.md', 'break.md'];

function read(file) {
  return fs.readFileSync(path.join(ROOT, file), 'utf8');
}

function htmlDocPages() {
  const block = read('gruntfile.js').match(/var htmlDocPages = \[([\s\S]*?)\]/);
  if (!block) throw new Error('htmlDocPages not found in gruntfile.js');
  return (block[1].match(/'([^']+)'/g) || []).map((s) => s.slice(1, -1));
}

function routes() {
  return (read(path.join('public', 'app', 'routes.js')).match(/\.when\('([^']+)'/g) || [])
    .map((s) => s.slice(7, -1));
}

// #!/devices/:id -> _devices_id.md
function pageForRoute(route) {
  const segments = route.replace(/^\//, '').split('/').map((s) => (s.startsWith(':') ? 'id' : s));
  return '_' + segments.join('_') + '.md';
}

function languages() {
  return fs.readdirSync(DOC_ROOT).filter((d) => fs.statSync(path.join(DOC_ROOT, d)).isDirectory()).sort();
}

function pagesIn(lang) {
  return fs.readdirSync(path.join(DOC_ROOT, lang))
    .filter((f) => f.endsWith('.md') && !SPECIAL.includes(f))
    .sort();
}

const findings = [];
const registered = htmlDocPages();
const langs = languages();
const primary = langs.includes('en') ? 'en' : langs[0];
const primaryPages = pagesIn(primary);

routes().forEach((route) => {
  const page = pageForRoute(route);
  if (!primaryPages.includes(page)) {
    findings.push(`route #!${route} has no documentation page (expected ${primary}/${page})`);
  }
});

primaryPages.forEach((page) => {
  if (!registered.includes(page)) {
    findings.push(`${page} is not in htmlDocPages, so it is absent from the combined manual and the PDF`);
  }
});

registered.forEach((page) => {
  if (!fs.existsSync(path.join(DOC_ROOT, primary, page))) {
    findings.push(`htmlDocPages lists ${page}, which does not exist in ${primary}/`);
  }
});

langs.filter((l) => l !== primary).forEach((lang) => {
  const present = pagesIn(lang);
  primaryPages.filter((p) => !present.includes(p)).forEach((page) => {
    findings.push(`${page} exists in ${primary}/ but not in ${lang}/`);
  });
});

if (findings.length === 0) {
  console.log('check-missing-doc: no findings');
  process.exit(0);
}

console.log(`check-missing-doc: ${findings.length} finding(s)`);
findings.forEach((f) => console.log('  ' + f));
process.exit(1);
