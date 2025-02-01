import { Behavior, registerBehavior } from "./index";
import { FocusTrapController } from "./focus-utils";

class DetailsModalBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.onClose = this.onClose.bind(this);
    this.onKeyDown = this.onKeyDown.bind(this);

    this.overlayLink = element.querySelector("a:has(.modal-overlay)");
    this.closeLink = element.querySelector(".modal-header .close");

    this.overlayLink.addEventListener("click", this.onClose);
    this.closeLink.addEventListener("click", this.onClose);
    document.addEventListener("keydown", this.onKeyDown);

    // Inert all other elements on the page to keep focus within the modal
    document
      .querySelectorAll("body > *:not(#details-modal)")
      .forEach((el) => el.setAttribute("inert", ""));

    const bookmarkId = element.dataset.bookmarkId;
    this.focusTrap = new FocusTrapController(
      element.querySelector(".modal-container"),
      [
        `ul.bookmark-list li[data-bookmark-id='${bookmarkId}'] a.view-action`,
        "ul.bookmark-list",
      ],
    );
  }

  destroy() {
    this.overlayLink.removeEventListener("click", this.onClose);
    this.closeLink.removeEventListener("click", this.onClose);
    document.removeEventListener("keydown", this.onKeyDown);

    // Clear inert attribute from all elements to allow focus outside the modal again
    document
      .querySelectorAll("body > *:not(#details-modal)")
      .forEach((el) => el.removeAttribute("inert"));

    // Clear focus trap and restore focus
    this.focusTrap.destroy();
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
