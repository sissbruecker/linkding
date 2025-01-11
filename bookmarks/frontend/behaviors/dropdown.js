import { Behavior, registerBehavior } from "./index";

class DropdownBehavior extends Behavior {
  constructor(element) {
    super(element);
    this.opened = false;
    this.onClick = this.onClick.bind(this);
    this.onOutsideClick = this.onOutsideClick.bind(this);
    this.onEscape = this.onEscape.bind(this);
    this.onFocusOut = this.onFocusOut.bind(this);

    // Prevent opening the dropdown automatically on focus, so that it only
    // opens on click then JS is enabled
    this.element.style.setProperty("--dropdown-focus-display", "none");
    this.element.addEventListener("keydown", this.onEscape);
    this.element.addEventListener("focusout", this.onFocusOut);

    this.toggle = element.querySelector(".dropdown-toggle");
    this.toggle.setAttribute("aria-expanded", "false");
    this.toggle.addEventListener("click", this.onClick);
  }

  destroy() {
    this.close();
    this.toggle.removeEventListener("click", this.onClick);
    this.element.removeEventListener("keydown", this.onEscape);
    this.element.removeEventListener("focusout", this.onFocusOut);
  }

  open() {
    this.opened = true;
    this.element.classList.add("active");
    this.toggle.setAttribute("aria-expanded", "true");
    document.addEventListener("click", this.onOutsideClick);
  }

  close() {
    this.opened = false;
    this.element.classList.remove("active");
    this.toggle.setAttribute("aria-expanded", "false");
    document.removeEventListener("click", this.onOutsideClick);
  }

  onClick() {
    if (this.opened) {
      this.close();
    } else {
      this.open();
    }
  }

  onOutsideClick(event) {
    if (!this.element.contains(event.target)) {
      this.close();
    }
  }

  onEscape(event) {
    if (event.key === "Escape" && this.opened) {
      event.preventDefault();
      this.close();
      this.toggle.focus();
    }
  }

  onFocusOut(event) {
    if (!this.element.contains(event.relatedTarget)) {
      this.close();
    }
  }
}

registerBehavior("ld-dropdown", DropdownBehavior);
