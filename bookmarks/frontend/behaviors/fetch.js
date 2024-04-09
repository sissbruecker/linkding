import { registerBehavior, swap } from "./index";

class FetchBehavior {
  constructor(element) {
    this.element = element;
    const eventName = element.getAttribute("ld-on");

    element.addEventListener(eventName, this.onFetch.bind(this));
  }

  async onFetch(event) {
    event.preventDefault();
    const url = this.element.getAttribute("ld-fetch");
    const html = await fetch(url).then((response) => response.text());

    const target = this.element.getAttribute("ld-target");
    swap(this.element, html, target);
  }
}

registerBehavior("ld-fetch", FetchBehavior);
