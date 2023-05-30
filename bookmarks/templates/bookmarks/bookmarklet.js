(function () {
  var bookmarkUrl = window.location;
  var applicationUrl = '{{ application_url }}';

  applicationUrl += '?url=' + encodeURIComponent(bookmarkUrl);
  applicationUrl += '&auto_close';

  window.open(applicationUrl);
})();
