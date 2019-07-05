(function() {
    var bookmarkUrl = window.location;
    var applicationUrl = '{{ application_url }}';

    applicationUrl += '?url=' + bookmarkUrl;
    applicationUrl += '&auto_close';

    window.open(applicationUrl);
})();
