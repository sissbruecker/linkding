import { Behavior, registerBehavior } from "./index";

class ModalBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.onClose = this.onClose.bind(this);
    this.onKeyDown = this.onKeyDown.bind(this);

    const overlayCloseLink = element.querySelector("a:has(.modal-overlay)");
    const closeButtonLink = element.querySelector("a:has(button.close)");
    overlayCloseLink.addEventListener("click", this.onClose);
    closeButtonLink.addEventListener("click", this.onClose);

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
      this.onClose(event);
    }
  }

  onClose(event) {
    event.preventDefault();
    this.element.classList.add("closing");
    this.element.addEventListener("animationend", (event) => {
      if (event.animationName === "fade-out") {
        this.element.remove();

        // Navigate to close URL if there is one
        const closeUrl = this.element.dataset.closeUrl;
        if (closeUrl) {
          Turbo.visit(closeUrl, { action: "replace" });
        }
      }
    }, { once: true });
  }
}

registerBehavior("ld-modal", ModalBehavior);
