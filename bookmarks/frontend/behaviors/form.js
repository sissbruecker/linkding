import { Behavior, fireEvents, registerBehavior } from "./index";

class AutoSubmitBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.submit = this.submit.bind(this);
    element.addEventListener("change", this.submit);
  }

  destroy() {
    this.element.removeEventListener("change", this.submit);
  }

  submit() {
    this.element.closest("form").requestSubmit();
  }
}

class UploadButton extends Behavior {
  constructor(element) {
    super(element);
    this.fileInput = element.nextElementSibling;

    this.onClick = this.onClick.bind(this);
    this.onChange = this.onChange.bind(this);

    element.addEventListener("click", this.onClick);
    this.fileInput.addEventListener("change", this.onChange);
  }

  onClick() {
    this.fileInput.click();
  }

  onChange() {
    const form = this.fileInput.closest("form");
    const event = new Event("submit", { cancelable: true });
    event.submitter = this.element;
    form.dispatchEvent(event);
  }
}

registerBehavior("ld-auto-submit", AutoSubmitBehavior);
registerBehavior("ld-upload-button", UploadButton);
