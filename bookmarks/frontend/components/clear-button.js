class ClearButton extends HTMLElement {
  connectedCallback() {
    requestAnimationFrame(() => {
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
    });
  }

  disconnectedCallback() {
    if (!this.field) {
      return;
    }
    this.removeEventListener("click", this.clear);
    this.field.removeEventListener("input", this.update);
    this.field.removeEventListener("value-changed", this.update);
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
