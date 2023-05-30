(function () {
  var bookmarkUrl = window.location;
  var bookmarkTitle = document.title;
  var applicationUrl = '{{ application_url }}';

  applicationUrl += '?url=' + encodeURIComponent(bookmarkUrl);
  applicationUrl += '&title=' + encodeURIComponent(bookmarkTitle);
  applicationUrl += '&auto_close';

  window.open(applicationUrl);
})();
