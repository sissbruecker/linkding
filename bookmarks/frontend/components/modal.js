import { FocusTrapController } from "../utils/focus.js";

export class Modal extends HTMLElement {
  connectedCallback() {
    requestAnimationFrame(() => {
      this.onClose = this.onClose.bind(this);
      this.onKeyDown = this.onKeyDown.bind(this);
      this.overlay = this.querySelector(".modal-overlay");
      this.closeButton = this.querySelector(".modal-header .close");

      this.overlay.addEventListener("click", this.onClose);
      this.closeButton.addEventListener("click", this.onClose);
      document.addEventListener("keydown", this.onKeyDown);

      this.setupScrollLock();
      this.focusTrap = new FocusTrapController(
        this.querySelector(".modal-container"),
      );
    });
  }

  disconnectedCallback() {
    this.overlay.removeEventListener("click", this.onClose);
    this.closeButton.removeEventListener("click", this.onClose);
    document.removeEventListener("keydown", this.onKeyDown);

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
    if (closeUrl) {
      Turbo.visit(closeUrl, { action: "replace", frame: frame });
    }
  }
}

customElements.define("ld-modal", Modal);
