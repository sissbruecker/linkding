import { LitElement } from "lit";

/**
 * Base class for custom elements that wrap existing server-rendered DOM.
 *
 * Handles timing issues where connectedCallback fires before child elements
 * are parsed during initial page load. With Turbo navigation, children are
 * always available, but on fresh page loads they may not be.
 *
 * Subclasses should override init() instead of connectedCallback().
 */
export class HeadlessElement extends HTMLElement {
  connectedCallback() {
    if (this.__initialized) {
      return;
    }
    this.__initialized = true;
    if (document.readyState === "loading") {
      document.addEventListener("turbo:load", () => this.init(), {
        once: true,
      });
    } else {
      this.init();
    }
  }

  init() {
    // Override in subclass
  }
}

let isTopFrameVisit = false;

document.addEventListener("turbo:visit", (event) => {
  const url = event.detail.url;
  isTopFrameVisit =
    document.querySelector(`turbo-frame[src="${url}"][target="_top"]`) !== null;
});

document.addEventListener("turbo:render", () => {
  isTopFrameVisit = false;
});

document.addEventListener("turbo:before-morph-element", (event) => {
  const parent = event.target?.parentElement;
  if (parent instanceof TurboLitElement) {
    // Prevent Turbo from morphing Lit elements contents, which would remove
    // elements rendered on the client side.
    event.preventDefault();
  }
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
