import { Behavior, registerBehavior } from "./index";

class DetailsModalBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.onClose = this.onClose.bind(this);
    this.onKeyDown = this.onKeyDown.bind(this);

    this.overlayLink = element.querySelector("a:has(.modal-overlay)");
    this.buttonLink = element.querySelector("a:has(button.close)");

    this.overlayLink.addEventListener("click", this.onClose);
    this.buttonLink.addEventListener("click", this.onClose);
    document.addEventListener("keydown", this.onKeyDown);
  }

  destroy() {
    this.overlayLink.removeEventListener("click", this.onClose);
    this.buttonLink.removeEventListener("click", this.onClose);
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
    this.element.addEventListener(
      "animationend",
      (event) => {
        if (event.animationName === "fade-out") {
          this.element.remove();

          const closeUrl = this.overlayLink.href;
          Turbo.visit(closeUrl, {
            action: "replace",
            frame: "details-modal",
          });
        }
      },
      { once: true },
    );
  }
}

registerBehavior("ld-details-modal", DetailsModalBehavior);
