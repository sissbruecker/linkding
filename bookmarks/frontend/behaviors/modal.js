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

    this.removeScrollLock();
    this.focusTrap.destroy();
  }

  init() {
    this.setupScrollLock();
    this.focusTrap = new FocusTrapController(
      this.element.querySelector(".modal-container"),
    );
  }

  setupScrollLock() {
    document.body.classList.add("scroll-lock");
  }

  removeScrollLock() {
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
    this.removeScrollLock();
    this.element.dispatchEvent(new CustomEvent("modal:close"));
  }
}
