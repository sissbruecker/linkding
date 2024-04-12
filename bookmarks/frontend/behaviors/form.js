import { Behavior, fireEvents, registerBehavior } from "./index";

class FormBehavior extends Behavior {
  constructor(element) {
    super(element);

    element.addEventListener("submit", this.onSubmit.bind(this));
  }

  async onSubmit(event) {
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

    const events = this.element.getAttribute("ld-fire");
    if (fireEvents) {
      fireEvents(events);
    }
  }
}

class AutoSubmitBehavior extends Behavior {
  constructor(element) {
    super(element);

    element.addEventListener("change", () => {
      const form = element.closest("form");
      form.dispatchEvent(new Event("submit", { cancelable: true }));
    });
  }
}

registerBehavior("ld-form", FormBehavior);
registerBehavior("ld-auto-submit", AutoSubmitBehavior);
