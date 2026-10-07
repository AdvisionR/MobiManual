#!/usr/bin/env node
// Renders the settings table of _policies_restrictions.md, in every language,
// from schema/policies/android-restrictions.json. The table sits between the
// two marker comments; everything else on the page is written by hand.
//
//   node scripts/render-restrictions.js          rewrite the tables
//   node scripts/render-restrictions.js --check  exit 1 if a table is stale

'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const SCHEMA = path.join(ROOT, 'schema', 'policies', 'android-restrictions.json');
const PAGE = '_policies_restrictions.md';
const BEGIN = '<!-- begin generated: android-restrictions -->';
const END = '<!-- end generated: android-restrictions -->';

// Column headings per language. Setting labels are not translated: the
// console shows the schema's labels as they are.
const HEADINGS = {
  en: ['Setting', 'Key', 'Default', 'Applies to'],
  tr: ['Ayar', 'Anahtar', 'Varsayılan', 'Geçerli olduğu'],
  de: ['Einstellung', 'Schlüssel', 'Standard', 'Gilt für']
};

function table(settings, headings) {
  const rows = settings.map((s) =>
    `| ${s.label} | \`${s.key}\` | \`${JSON.stringify(s.default)}\` | ${s.applies_to.join(', ')} |`);
  return [`| ${headings.join(' | ')} |`, '|---|---|---|---|', ...rows].join('\n');
}

const settings = JSON.parse(fs.readFileSync(SCHEMA, 'utf8')).settings;
const check = process.argv.includes('--check');
let stale = 0;

Object.keys(HEADINGS).forEach((lang) => {
  const file = path.join(ROOT, 'public', 'doc', lang, PAGE);
  if (!fs.existsSync(file)) return;
  const text = fs.readFileSync(file, 'utf8');
  const start = text.indexOf(BEGIN);
  const end = text.indexOf(END);
  if (start < 0 || end < start) throw new Error(`${lang}/${PAGE}: generated markers not found`);
  const rendered = text.slice(0, start + BEGIN.length) + '\n' + table(settings, HEADINGS[lang]) + '\n' + text.slice(end);
  if (rendered !== text) {
    stale += 1;
    if (check) console.log(`${lang}/${PAGE} is stale`);
    else fs.writeFileSync(file, rendered);
  }
});

process.exit(check && stale ? 1 : 0);
