let keyboardActive = false;

window.addEventListener(
  "keydown",
  () => {
    keyboardActive = true;
  },
  { capture: true },
);

window.addEventListener(
  "mousedown",
  () => {
    keyboardActive = false;
  },
  { capture: true },
);

export function isKeyboardActive() {
  return keyboardActive;
}

export class FocusTrapController {
  constructor(element) {
    this.element = element;
    this.focusableElements = this.element.querySelectorAll(
      'a[href]:not([disabled]), button:not([disabled]), textarea:not([disabled]), input[type="text"]:not([disabled]), input[type="radio"]:not([disabled]), input[type="checkbox"]:not([disabled]), select:not([disabled])',
    );
    this.firstFocusableElement = this.focusableElements[0];
    this.lastFocusableElement =
      this.focusableElements[this.focusableElements.length - 1];

    this.onKeyDown = this.onKeyDown.bind(this);

    this.firstFocusableElement.focus({ focusVisible: keyboardActive });
    this.element.addEventListener("keydown", this.onKeyDown);
  }

  destroy() {
    this.element.removeEventListener("keydown", this.onKeyDown);
  }

  onKeyDown(event) {
    if (event.key !== "Tab") {
      return;
    }
    if (event.shiftKey) {
      if (document.activeElement === this.firstFocusableElement) {
        event.preventDefault();
        this.lastFocusableElement.focus();
      }
    } else {
      if (document.activeElement === this.lastFocusableElement) {
        event.preventDefault();
        this.firstFocusableElement.focus();
      }
    }
  }
}

let afterPageLoadFocusTarget = [];
let firstPageLoad = true;

export function setAfterPageLoadFocusTarget(...targets) {
  afterPageLoadFocusTarget = targets;
}

function programmaticFocus(element) {
  // Ensure element is focusable
  // Hide focus outline if element is not focusable by default - might
  // reconsider this later
  const isFocusable = element.tabIndex >= 0;
  if (!isFocusable) {
    // Apparently the default tabIndex is -1, even though an element is still
    // not focusable with that. Setting an explicit -1 also sets the attribute
    // and the element becomes focusable.
    element.tabIndex = -1;
    // `focusVisible` is not supported in all browsers, so hide the outline manually
    element.style["outline"] = "none";
  }
  element.focus({
    focusVisible: isKeyboardActive() && isFocusable,
    preventScroll: true,
  });
}

// Register global listener for navigation and try to focus an element that
// results in a meaningful announcement.
document.addEventListener("turbo:load", () => {
  // Ignore initial page load to let the browser handle announcements
  if (firstPageLoad) {
    firstPageLoad = false;
    return;
  }

  // Check if there is an explicit focus target for the next page load
  for (const target of afterPageLoadFocusTarget) {
    const element = document.querySelector(target);
    if (element) {
      programmaticFocus(element);
      return;
    }
  }
  afterPageLoadFocusTarget = [];

  // If there is some autofocus element, let the browser handle it
  const autofocus = document.querySelector("[autofocus]");
  if (autofocus) {
    return;
  }

  // If there is a toast as a result of some action, focus it
  const toast = document.querySelector(".toast");
  if (toast) {
    programmaticFocus(toast);
    return;
  }

  // Otherwise go with main
  const main = document.querySelector("main");
  if (main) {
    programmaticFocus(main);
  }
});
