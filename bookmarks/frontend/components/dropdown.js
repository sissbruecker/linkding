import { HeadlessElement } from "../utils/element.js";

class Dropdown extends HeadlessElement {
  constructor() {
    super();
    this.opened = false;
    this.onClick = this.onClick.bind(this);
    this.onOutsideClick = this.onOutsideClick.bind(this);
    this.onEscape = this.onEscape.bind(this);
    this.onFocusOut = this.onFocusOut.bind(this);
  }

  init() {
    // Prevent opening the dropdown automatically on focus, so that it only
    // opens on click when JS is enabled
    this.style.setProperty("--dropdown-focus-display", "none");
    this.addEventListener("keydown", this.onEscape);
    this.addEventListener("focusout", this.onFocusOut);

    this.toggle = this.querySelector(".dropdown-toggle");
    this.toggle.setAttribute("aria-expanded", "false");
    this.toggle.addEventListener("click", this.onClick);
  }

  disconnectedCallback() {
    this.close();
  }

  open() {
    this.opened = true;
    this.classList.add("active");
    this.toggle.setAttribute("aria-expanded", "true");
    document.addEventListener("click", this.onOutsideClick);
  }

  close() {
    this.opened = false;
    this.classList.remove("active");
    this.toggle?.setAttribute("aria-expanded", "false");
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
    if (!this.contains(event.target)) {
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
    if (!this.contains(event.relatedTarget)) {
      this.close();
    }
  }
}

customElements.define("ld-dropdown", Dropdown);
