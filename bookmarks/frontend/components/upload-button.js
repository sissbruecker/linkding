import { HeadlessElement } from "../utils/element.js";

class UploadButton extends HeadlessElement {
  init() {
    this.onClick = this.onClick.bind(this);
    this.onChange = this.onChange.bind(this);

    this.button = this.querySelector('button[type="submit"]');
    this.button.addEventListener("click", this.onClick);

    this.fileInput = this.querySelector('input[type="file"]');
    this.fileInput.addEventListener("change", this.onChange);
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
    this.closest("form").requestSubmit(this.button);
    // remove selected file so it doesn't get submitted again
    this.fileInput.value = "";
  }
}

customElements.define("ld-upload-button", UploadButton);
