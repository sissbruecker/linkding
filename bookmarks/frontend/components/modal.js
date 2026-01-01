import { FocusTrapController } from "../utils/focus.js";
import { HeadlessElement } from "../utils/element.js";

export class Modal extends HeadlessElement {
  init() {
    this.onClose = this.onClose.bind(this);
    this.onKeyDown = this.onKeyDown.bind(this);

    this.querySelectorAll("[data-close-modal]").forEach((btn) => {
      btn.addEventListener("click", this.onClose);
    });
    this.addEventListener("keydown", this.onKeyDown);

    this.setupScrollLock();
    this.focusTrap = new FocusTrapController(
      this.querySelector(".modal-container"),
    );
  }

  disconnectedCallback() {
    this.removeScrollLock();
    this.focusTrap.destroy();
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
    this.classList.add("closing");
    this.addEventListener(
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
    this.remove();
    this.dispatchEvent(new CustomEvent("modal:close"));

    // Navigate to close URL
    const closeUrl = this.dataset.closeUrl;
    const frame = this.dataset.turboFrame;
    const action = this.dataset.turboAction || "replace";
    if (closeUrl) {
      Turbo.visit(closeUrl, { action, frame: frame });
    }
  }
}

customElements.define("ld-modal", Modal);
