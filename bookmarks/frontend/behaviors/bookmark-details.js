import { registerBehavior } from "./index";

class BookmarkDetails {
  constructor(element) {
    this.form = element.querySelector(".status form");
    if (!this.form) {
      // Form may not exist if user does not own the bookmark
      return;
    }
    this.form.addEventListener("submit", (event) => {
      event.preventDefault();
      this.submitForm();
    });

    const inputs = this.form.querySelectorAll("input");
    inputs.forEach((input) => {
      input.addEventListener("change", () => {
        this.submitForm();
      });
    });
  }

  async submitForm() {
    const url = this.form.action;
    const formData = new FormData(this.form);

    await fetch(url, {
      method: "POST",
      body: formData,
      redirect: "manual", // ignore redirect
    });

    // Refresh bookmark page if it exists
    document.dispatchEvent(new CustomEvent("bookmark-page-refresh"));
  }
}

registerBehavior("ld-bookmark-details", BookmarkDetails);
