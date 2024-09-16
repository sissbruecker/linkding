import { Behavior, registerBehavior } from "./index";

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

  destroy() {
    this.element.removeEventListener("click", this.onClick);
    this.fileInput.removeEventListener("change", this.onChange);
  }

  onClick(event) {
    event.preventDefault();
    this.fileInput.click();
  }

  onChange() {
    // Check if the file input has a file selected
    if (!this.fileInput.files.length) {
      return;
    }
    const form = this.fileInput.closest("form");
    form.requestSubmit(this.element);
    // remove selected file so it doesn't get submitted again
    this.fileInput.value = "";
  }
}

registerBehavior("ld-auto-submit", AutoSubmitBehavior);
registerBehavior("ld-upload-button", UploadButton);
