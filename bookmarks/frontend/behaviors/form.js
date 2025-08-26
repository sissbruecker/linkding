import { Behavior, registerBehavior } from "./index";

class FormSubmit extends Behavior {
  constructor(element) {
    super(element);

    this.onKeyDown = this.onKeyDown.bind(this);
    this.element.addEventListener("keydown", this.onKeyDown);
  }

  destroy() {
    this.element.removeEventListener("keydown", this.onKeyDown);
  }

  onKeyDown(event) {
    // Check for Ctrl/Cmd + Enter combination
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      event.stopPropagation();
      this.element.requestSubmit();
    }
  }
}

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

// Resets form controls to their initial values before Turbo caches the DOM.
// Useful for filter forms where navigating back would otherwise still show
// values from after the form submission, which means the filters would be out
// of sync with the URL.
class FormResetBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.controls = this.element.querySelectorAll("input, select");
    this.controls.forEach((control) => {
      if (control.type === "checkbox" || control.type === "radio") {
        control.__initialValue = control.checked;
      } else {
        control.__initialValue = control.value;
      }
    });
  }

  destroy() {
    this.controls.forEach((control) => {
      if (control.type === "checkbox" || control.type === "radio") {
        control.checked = control.__initialValue;
      } else {
        control.value = control.__initialValue;
      }
      delete control.__initialValue;
    });
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

registerBehavior("ld-form-submit", FormSubmit);
registerBehavior("ld-auto-submit", AutoSubmitBehavior);
registerBehavior("ld-form-reset", FormResetBehavior);
registerBehavior("ld-upload-button", UploadButton);
