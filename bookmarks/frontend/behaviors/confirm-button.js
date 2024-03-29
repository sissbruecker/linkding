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

    const container = document.createElement("span");
    container.className = "confirmation";

    const icon = this.button.getAttribute("confirm-icon");
    if (icon) {
      const iconElement = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "svg",
      );
      iconElement.style.width = "16px";
      iconElement.style.height = "16px";
      iconElement.innerHTML = `<use xlink:href="#${icon}"></use>`;
      container.append(iconElement);
    }

    const question = this.button.getAttribute("confirm-question");
    if (question) {
      const questionElement = document.createElement("span");
      questionElement.innerText = question;
      container.append(question);
    }

    const buttonClasses = Array.from(this.button.classList.values())
      .filter((cls) => cls.startsWith("btn"))
      .join(" ");

    const cancelButton = document.createElement(this.button.nodeName);
    cancelButton.type = "button";
    cancelButton.innerText = question ? "No" : "Cancel";
    cancelButton.className = `${buttonClasses} mr-1`;
    cancelButton.addEventListener("click", this.reset.bind(this));

    const confirmButton = document.createElement(this.button.nodeName);
    confirmButton.type = this.button.dataset.type;
    confirmButton.name = this.button.dataset.name;
    confirmButton.value = this.button.dataset.value;
    confirmButton.innerText = question ? "Yes" : "Confirm";
    confirmButton.className = buttonClasses;
    confirmButton.addEventListener("click", this.reset.bind(this));

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
