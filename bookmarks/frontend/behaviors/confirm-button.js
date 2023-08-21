import { registerBehavior } from "./index";

class ConfirmButtonBehavior {
  constructor(element) {
    const button = element;
    button.dataset.type = button.type;
    button.dataset.name = button.name;
    button.dataset.value = button.value;
    button.removeAttribute("type");
    button.removeAttribute("name");
    button.removeAttribute("value");
    button.addEventListener("click", this.onClick.bind(this));
    this.button = button;
  }

  onClick(event) {
    event.preventDefault();

    const cancelButton = document.createElement(this.button.nodeName);
    cancelButton.type = "button";
    cancelButton.innerText = "Cancel";
    cancelButton.className = "btn btn-link btn-sm mr-1";
    cancelButton.addEventListener("click", this.reset.bind(this));

    const confirmButton = document.createElement(this.button.nodeName);
    confirmButton.type = this.button.dataset.type;
    confirmButton.name = this.button.dataset.name;
    confirmButton.value = this.button.dataset.value;
    confirmButton.innerText = "Confirm";
    confirmButton.className = "btn btn-link btn-sm";
    confirmButton.addEventListener("click", this.reset.bind(this));

    const container = document.createElement("span");
    container.className = "confirmation";
    container.append(cancelButton, confirmButton);
    this.container = container;

    this.button.before(container);
    this.button.classList.add("d-none");
  }

  reset() {
    setTimeout(() => {
      this.container.remove();
      this.button.classList.remove("d-none");
    });
  }
}

registerBehavior("ld-confirm-button", ConfirmButtonBehavior);
