export function debounce(callback, delay = 250) {
  let timeoutId;
  const debounced = (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      timeoutId = null;
      callback(...args);
    }, delay);
  };
  debounced.cancel = () => {
    clearTimeout(timeoutId);
    timeoutId = null;
  };
  return debounced;
}

export function clampText(text, maxChars = 30) {
  if (!text || text.length <= 30) return text;

  return text.substr(0, maxChars) + "...";
}

export function getCurrentWordBounds(input) {
  const text = input.value;
  const end = input.selectionStart;
  let start = end;

  let currentChar = text.charAt(start - 1);

  while (currentChar && currentChar !== " " && start > 0) {
    start--;
    currentChar = text.charAt(start - 1);
  }

  return { start, end };
}

export function getCurrentWord(input) {
  const bounds = getCurrentWordBounds(input);

  return input.value.substring(bounds.start, bounds.end);
}
