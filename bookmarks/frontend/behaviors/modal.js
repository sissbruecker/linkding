import { Behavior } from "./index";
import { FocusTrapController } from "./focus-utils";

export class ModalBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.onClose = this.onClose.bind(this);
    this.onKeyDown = this.onKeyDown.bind(this);

    this.overlay = element.querySelector(".modal-overlay");
    this.closeButton = element.querySelector(".modal-header .close");

    this.overlay.addEventListener("click", this.onClose);
    this.closeButton.addEventListener("click", this.onClose);
    document.addEventListener("keydown", this.onKeyDown);

    this.init();
  }

  destroy() {
    this.overlay.removeEventListener("click", this.onClose);
    this.closeButton.removeEventListener("click", this.onClose);
    document.removeEventListener("keydown", this.onKeyDown);

    this.clearInert();
    this.focusTrap.destroy();
  }

  init() {
    this.setupInert();
    this.focusTrap = new FocusTrapController(
      this.element.querySelector(".modal-container"),
    );
  }

  setupInert() {
    // Inert all other elements on the page
    document
      .querySelectorAll("body > *:not(.modals)")
      .forEach((el) => el.setAttribute("inert", ""));
    // Lock scroll on the body
    document.body.classList.add("scroll-lock");
  }

  clearInert() {
    // Clear inert attribute from all elements to allow focus outside the modal again
    document
      .querySelectorAll("body > *")
      .forEach((el) => el.removeAttribute("inert"));
    // Remove scroll lock from the body
    document.body.classList.remove("scroll-lock");
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
