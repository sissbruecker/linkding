import { LitElement } from "lit";

let isTopFrameVisit = false;

document.addEventListener("turbo:visit", (event) => {
  const url = event.detail.url;
  isTopFrameVisit =
    document.querySelector(`turbo-frame[src="${url}"][target="_top"]`) !== null;
});

document.addEventListener("turbo:render", () => {
  isTopFrameVisit = false;
});

export class TurboLitElement extends LitElement {
  constructor() {
    super();
    this.__prepareForCache = this.__prepareForCache.bind(this);
  }

  createRenderRoot() {
    return this; // Render to light DOM
  }

  connectedCallback() {
    document.addEventListener("turbo:before-cache", this.__prepareForCache);
    super.connectedCallback();
  }

  disconnectedCallback() {
    document.removeEventListener("turbo:before-cache", this.__prepareForCache);
    super.disconnectedCallback();
  }

  __prepareForCache() {
    // Remove rendered contents before caching, otherwise restoring the DOM from
    // cache will result in duplicated contents. Turbo also fires before-cache
    // when rendering a frame that does target the top frame, in which case we
    // want to keep the contents.
    if (!isTopFrameVisit) {
      this.innerHTML = "";
    }
  }
}
