(function () {
  const bookmarkUrl = window.location;

  let applicationUrl = '{{ application_url }}';
  applicationUrl += '?url=' + encodeURIComponent(bookmarkUrl);
  applicationUrl += '&auto_close';

  window.open(applicationUrl);
})();
