import { Behavior } from "./index";
import { FocusTrapController } from "./focus-utils";

export class ModalBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.onClose = this.onClose.bind(this);
    this.onKeyDown = this.onKeyDown.bind(this);

    this.overlayLink = element.querySelector("a:has(.modal-overlay)");
    this.closeLink = element.querySelector(".modal-header .close");

    this.overlayLink.addEventListener("click", this.onClose);
    this.closeLink.addEventListener("click", this.onClose);
    document.addEventListener("keydown", this.onKeyDown);

    this.setupInert();
    this.focusTrap = new FocusTrapController(
      element.querySelector(".modal-container"),
    );
  }

  destroy() {
    this.overlayLink.removeEventListener("click", this.onClose);
    this.closeLink.removeEventListener("click", this.onClose);
    document.removeEventListener("keydown", this.onKeyDown);

    this.clearInert();
    this.focusTrap.destroy();
  }

  setupInert() {
    // Inert all other elements on the page
    document
      .querySelectorAll("body > *:not(.modals)")
      .forEach((el) => el.setAttribute("inert", ""));
  }

  clearInert() {
    // Clear inert attribute from all elements to allow focus outside the modal again
    document
      .querySelectorAll("body > *")
      .forEach((el) => el.removeAttribute("inert"));
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
          this.doClose();
        }
      },
      { once: true },
    );
  }

  doClose() {
    this.element.remove();
    this.clearInert();
    this.element.dispatchEvent(new CustomEvent("modal:close"));
  }
}
