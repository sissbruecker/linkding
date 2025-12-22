import { Behavior, registerBehavior } from "./index";
import { FocusTrapController, isKeyboardActive } from "./focus-utils";
import { PositionController } from "./position-controller";

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

    this.positionController = new PositionController({
      anchor: this.element,
      overlay: menu,
      arrow: arrow,
      offset: 12,
    });
    this.positionController.enable();
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
    this.positionController.disable();
    this.focusTrap.destroy();
    this.dropdown.remove();
    this.element.focus({ focusVisible: isKeyboardActive() });
    this.opened = false;
  }
}

registerBehavior("ld-confirm-button", ConfirmButtonBehavior);
