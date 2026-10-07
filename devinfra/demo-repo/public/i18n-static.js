// Labels for the pages served outside the console app (login.html): fills
// every [data-i18n] element from i18n/<lang>.json, in the browser's language.
(function () {
  var lang = (navigator.language || 'en').slice(0, 2);
  if (['en', 'tr', 'de'].indexOf(lang) < 0) lang = 'en';
  var reason = new URLSearchParams(location.search).get('reason');

  fetch('i18n/' + lang + '.json').then(function (r) { return r.json(); }).then(function (labels) {
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var text = el.getAttribute('data-i18n').split('.').reduce(function (o, k) { return o && o[k]; }, labels);
      el.textContent = (text || '').replace('{{minutes}}', '15');
    });
    document.querySelectorAll('[data-reason]').forEach(function (el) {
      el.hidden = el.getAttribute('data-reason') !== reason;
    });
  });
})();
