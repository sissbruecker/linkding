import { registerBehavior } from "./index";

class ModalBehavior {
  constructor(element) {
    this.element = element;

    const modalOverlay = element.querySelector(".modal-overlay");
    const closeButton = element.querySelector("button.close");
    modalOverlay.addEventListener("click", this.onClose.bind(this));
    closeButton.addEventListener("click", this.onClose.bind(this));
  }

  onClose() {
    this.element.classList.add("closing");
    this.element.addEventListener("animationend", (event) => {
      if (event.animationName === "fade-out") {
        this.element.remove();
      }
    });
  }
}

registerBehavior("ld-modal", ModalBehavior);
