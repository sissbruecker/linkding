import { Behavior, registerBehavior } from "./index";
import { FocusTrapController, isKeyboardActive } from "./focus-utils";

let confirmId = 0;

function nextConfirmId() {
  return `confirm-${confirmId++}`;
}

class ConfirmButtonBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.onClick = this.onClick.bind(this);
    this.element.addEventListener("click", this.onClick);
  }

  destroy() {
    if (this.opened) {
      this.close();
    }
    this.element.removeEventListener("click", this.onClick);
  }

  onClick(event) {
    event.preventDefault();

    if (this.opened) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    const dropdown = document.createElement("div");
    dropdown.className = "dropdown confirm-dropdown active";

    const confirmId = nextConfirmId();
    const questionId = `${confirmId}-question`;

    const menu = document.createElement("div");
    menu.className = "menu with-arrow";
    menu.role = "alertdialog";
    menu.setAttribute("aria-modal", "true");
    menu.setAttribute("aria-labelledby", questionId);
    menu.addEventListener("keydown", this.onMenuKeyDown.bind(this));

    const question = document.createElement("span");
    question.id = questionId;
    question.textContent =
      this.element.getAttribute("ld-confirm-question") || "Are you sure?";
    question.style.fontWeight = "bold";

    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.type = "button";
    cancelButton.className = "btn";
    cancelButton.tabIndex = 0;
    cancelButton.addEventListener("click", () => this.close());

    const confirmButton = document.createElement("button");
    confirmButton.textContent = "Confirm";
    confirmButton.type = "submit";
    confirmButton.name = this.element.name;
    confirmButton.value = this.element.value;
    confirmButton.className = "btn btn-error";
    confirmButton.addEventListener("click", () => this.confirm());

    const arrow = document.createElement("div");
    arrow.className = "menu-arrow";

    menu.append(question, cancelButton, confirmButton, arrow);
    dropdown.append(menu);
    document.body.append(dropdown);

    this.positionController = new AnchorPositionController(this.element, menu);
    this.focusTrap = new FocusTrapController(menu);
    this.dropdown = dropdown;
    this.opened = true;
  }

  onMenuKeyDown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      this.close();
    }
  }

  confirm() {
    this.element.closest("form").requestSubmit(this.element);
    this.close();
  }

  close() {
    if (!this.opened) return;
    this.positionController.destroy();
    this.focusTrap.destroy();
    this.dropdown.remove();
    this.element.focus({ focusVisible: isKeyboardActive() });
    this.opened = false;
  }
}

class AnchorPositionController {
  constructor(anchor, overlay) {
    this.anchor = anchor;
    this.overlay = overlay;

    this.handleScroll = this.handleScroll.bind(this);
    window.addEventListener("scroll", this.handleScroll, { capture: true });

    this.updatePosition();
  }

  handleScroll() {
    if (this.debounce) {
      return;
    }

    this.debounce = true;

    requestAnimationFrame(() => {
      this.updatePosition();
      this.debounce = false;
    });
  }

  updatePosition() {
    const anchorRect = this.anchor.getBoundingClientRect();
    const overlayRect = this.overlay.getBoundingClientRect();
    const bufferX = 10;
    const bufferY = 30;

    let left = anchorRect.left - (overlayRect.width - anchorRect.width) / 2;
    const initialLeft = left;
    const overflowLeft = left < bufferX;
    const overflowRight =
      left + overlayRect.width > window.innerWidth - bufferX;

    if (overflowLeft) {
      left = bufferX;
    } else if (overflowRight) {
      left = window.innerWidth - overlayRect.width - bufferX;
    }

    const delta = initialLeft - left;
    this.overlay.style.setProperty("--arrow-offset", `${delta}px`);

    let top = anchorRect.bottom;
    const overflowBottom =
      top + overlayRect.height > window.innerHeight - bufferY;

    if (overflowBottom) {
      top = anchorRect.top - overlayRect.height;
      this.overlay.classList.remove("top-aligned");
      this.overlay.classList.add("bottom-aligned");
    } else {
      this.overlay.classList.remove("bottom-aligned");
      this.overlay.classList.add("top-aligned");
    }

    this.overlay.style.left = `${left}px`;
    this.overlay.style.top = `${top}px`;
  }

  destroy() {
    window.removeEventListener("scroll", this.handleScroll, { capture: true });
  }
}

registerBehavior("ld-confirm-button", ConfirmButtonBehavior);
