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
