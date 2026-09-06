// Translated strings for use in JavaScript are provided by the server as data
// attributes on the <html> element, see shared/layout.html. The fallback is
// used when the attribute is not available, e.g. in pages that do not use the
// shared layout.
export function translate(key, fallback) {
  return document.documentElement.dataset[key] || fallback;
}
