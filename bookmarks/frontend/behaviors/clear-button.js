import { Behavior, registerBehavior } from "./index";

class ClearButtonBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.field = document.getElementById(element.dataset.for);
    if (!this.field) {
      console.error(`Field with ID ${element.dataset.for} not found`);
      return;
    }

    this.update = this.update.bind(this);
    this.clear = this.clear.bind(this);

    this.element.addEventListener("click", this.clear);
    this.field.addEventListener("input", this.update);
    this.field.addEventListener("value-changed", this.update);
    this.update();
  }

  destroy() {
    if (!this.field) {
      return;
    }
    this.element.removeEventListener("click", this.clear);
    this.field.removeEventListener("input", this.update);
    this.field.removeEventListener("value-changed", this.update);
  }

  update() {
    this.element.style.display = this.field.value ? "inline-flex" : "none";
  }

  clear() {
    this.field.value = "";
    this.field.focus();
    this.update();
  }
}

registerBehavior("ld-clear-button", ClearButtonBehavior);
