import { Behavior, registerBehavior } from "./index";

class ModalBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.onClose = this.onClose.bind(this);
    this.onKeyDown = this.onKeyDown.bind(this);

    const modalOverlay = element.querySelector(".modal-overlay");
    const closeButton = element.querySelector("button.close");
    modalOverlay.addEventListener("click", this.onClose);
    closeButton.addEventListener("click", this.onClose);

    document.addEventListener("keydown", this.onKeyDown);
  }

  destroy() {
    document.removeEventListener("keydown", this.onKeyDown);
  }

  onKeyDown(event) {
    // Skip if event occurred within an input element
    const targetNodeName = event.target.nodeName;
    const isInputTarget =
      targetNodeName === "INPUT" ||
      targetNodeName === "SELECT" ||
      targetNodeName === "TEXTAREA";

    if (isInputTarget) {
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      this.onClose();
    }
  }

  onClose() {
    document.removeEventListener("keydown", this.onKeyDown);
    this.element.classList.add("closing");
    this.element.addEventListener("animationend", (event) => {
      if (event.animationName === "fade-out") {
        this.element.remove();
      }
    });
  }
}

registerBehavior("ld-modal", ModalBehavior);
