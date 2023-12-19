import { registerBehavior } from "./index";

class DropdownBehavior {
  constructor(element) {
    this.element = element;
    this.opened = false;
    this.onOutsideClick = this.onOutsideClick.bind(this);

    const toggle = element.querySelector(".dropdown-toggle");
    toggle.addEventListener("click", () => {
      if (this.opened) {
        this.close();
      } else {
        this.open();
      }
    });
  }

  open() {
    this.element.classList.add("active");
    document.addEventListener("click", this.onOutsideClick);
  }

  close() {
    this.element.classList.remove("active");
    document.removeEventListener("click", this.onOutsideClick);
  }

  onOutsideClick(event) {
    if (!this.element.contains(event.target)) {
      this.close();
    }
  }
}

registerBehavior("ld-dropdown", DropdownBehavior);
