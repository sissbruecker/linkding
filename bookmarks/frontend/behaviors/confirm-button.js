import { Behavior, registerBehavior } from "./index";

class ConfirmButtonBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.onClick = this.onClick.bind(this);
    element.addEventListener("click", this.onClick);
  }

  destroy() {
    this.reset();
    this.element.removeEventListener("click", this.onClick);
  }

  onClick(event) {
    event.preventDefault();
    Behavior.interacting = true;

    const container = document.createElement("span");
    container.className = "confirmation";

    const icon = this.element.getAttribute("ld-confirm-icon");
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

    const question = this.element.getAttribute("ld-confirm-question");
    if (question) {
      const questionElement = document.createElement("span");
      questionElement.innerText = question;
      container.append(question);
    }

    const buttonClasses = Array.from(this.element.classList.values())
      .filter((cls) => cls.startsWith("btn"))
      .join(" ");

    const cancelButton = document.createElement(this.element.nodeName);
    cancelButton.type = "button";
    cancelButton.innerText = question ? "No" : "Cancel";
    cancelButton.className = `${buttonClasses} mr-1`;
    cancelButton.addEventListener("click", this.reset.bind(this));

    const confirmButton = document.createElement(this.element.nodeName);
    confirmButton.type = this.element.type;
    confirmButton.name = this.element.name;
    confirmButton.value = this.element.value;
    confirmButton.innerText = question ? "Yes" : "Confirm";
    confirmButton.className = buttonClasses;
    confirmButton.addEventListener("click", this.reset.bind(this));

    container.append(cancelButton, confirmButton);
    this.container = container;

    this.element.before(container);
    this.element.classList.add("d-none");
  }

  reset() {
    setTimeout(() => {
      Behavior.interacting = false;
      if (this.container) {
        this.container.remove();
        this.container = null;
      }
      this.element.classList.remove("d-none");
    });
  }
}

registerBehavior("ld-confirm-button", ConfirmButtonBehavior);
