import { Behavior, fireEvents, registerBehavior, swap } from "./index";

class FetchBehavior extends Behavior {
  constructor(element) {
    super(element);

    const eventName = element.getAttribute("ld-on");
    const interval = parseInt(element.getAttribute("ld-interval")) * 1000;

    this.onFetch = this.onFetch.bind(this);
    this.onInterval = this.onInterval.bind(this);

    element.addEventListener(eventName, this.onFetch);
    if (interval) {
      this.intervalId = setInterval(this.onInterval, interval);
    }
  }

  destroy() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }

  async onFetch(maybeEvent) {
    if (maybeEvent) {
      maybeEvent.preventDefault();
    }
    const url = this.element.getAttribute("ld-fetch");
    const html = await fetch(url).then((response) => response.text());

    const target = this.element.getAttribute("ld-target");
    const select = this.element.getAttribute("ld-select");
    swap(this.element, html, { target, select });

    const events = this.element.getAttribute("ld-fire");
    fireEvents(events);
  }

  onInterval() {
    if (Behavior.interacting) {
      return;
    }
    this.onFetch();
  }
}

registerBehavior("ld-fetch", FetchBehavior);
