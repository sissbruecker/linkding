import { registerBehavior, swap } from "./index";

class FormBehavior {
  constructor(element) {
    this.element = element;
    element.addEventListener("submit", this.onFormSubmit.bind(this));
  }

  async onFormSubmit(event) {
    event.preventDefault();

    const url = this.element.action;
    const formData = new FormData(this.element);
    if (event.submitter) {
      formData.append(event.submitter.name, event.submitter.value);
    }

    await fetch(url, {
      method: "POST",
      body: formData,
      redirect: "manual", // ignore redirect
    });

    // Dispatch refresh events
    const refreshEvents = this.element.getAttribute("refresh-events");
    if (refreshEvents) {
      refreshEvents.split(",").forEach((eventName) => {
        document.dispatchEvent(new CustomEvent(eventName));
      });
    }

    // Refresh form
    await this.refresh();
  }

  async refresh() {
    const refreshUrl = this.element.getAttribute("refresh-url");
    const html = await fetch(refreshUrl).then((response) => response.text());
    swap(this.element, html);
  }
}

class FormAutoSubmitBehavior {
  constructor(element) {
    this.element = element;
    this.element.addEventListener("change", () => {
      const form = this.element.closest("form");
      form.dispatchEvent(new Event("submit", { cancelable: true }));
    });
  }
}

registerBehavior("ld-form", FormBehavior);
registerBehavior("ld-form-auto-submit", FormAutoSubmitBehavior);
