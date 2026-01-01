import { HeadlessElement } from "../utils/element";

class ClearButton extends HeadlessElement {
  init() {
    this.field = document.getElementById(this.dataset.for);
    if (!this.field) {
      console.error(`Field with ID ${this.dataset.for} not found`);
      return;
    }
    this.update = this.update.bind(this);
    this.clear = this.clear.bind(this);

    this.addEventListener("click", this.clear);
    this.field.addEventListener("input", this.update);
    this.field.addEventListener("value-changed", this.update);
    this.update();
  }

  update() {
    this.style.display = this.field.value ? "inline" : "none";
  }

  clear() {
    this.field.value = "";
    this.field.focus();
    this.update();
  }
}

customElements.define("ld-clear-button", ClearButton);
