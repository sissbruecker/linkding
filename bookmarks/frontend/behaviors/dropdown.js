import { Behavior, registerBehavior } from "./index";

class DropdownBehavior extends Behavior {
  constructor(element) {
    super(element);
    this.opened = false;
    this.onClick = this.onClick.bind(this);
    this.onOutsideClick = this.onOutsideClick.bind(this);

    this.toggle = element.querySelector(".dropdown-toggle");
    this.toggle.addEventListener("click", this.onClick);
  }

  destroy() {
    this.close();
    this.toggle.removeEventListener("click", this.onClick);
  }

  open() {
    this.element.classList.add("active");
    document.addEventListener("click", this.onOutsideClick);
  }

  close() {
    this.element.classList.remove("active");
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
}

registerBehavior("ld-dropdown", DropdownBehavior);
