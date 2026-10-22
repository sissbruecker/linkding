const messages = (() => {
  const element = document.getElementById("ld-i18n");
  if (!element) return {};
  try {
    return JSON.parse(element.textContent);
  } catch (error) {
    console.error("Failed to parse i18n messages", error);
    return {};
  }
})();

export function t(key, fallback = "") {
  const message = messages[key];
  return message === undefined ? fallback : message;
}
