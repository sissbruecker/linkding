import { html, render } from "lit";
import { Modal } from "./modal.js";
import { HeadlessElement } from "../utils/element.js";
import { isKeyboardActive } from "../utils/focus.js";

class FilterDrawerTrigger extends HeadlessElement {
  init() {
    this.onClick = this.onClick.bind(this);
    this.addEventListener("click", this.onClick.bind(this));
  }

  onClick() {
    const modal = document.createElement("ld-filter-drawer");
    document.body.querySelector(".modals").appendChild(modal);
  }
}

customElements.define("ld-filter-drawer-trigger", FilterDrawerTrigger);

class FilterDrawer extends Modal {
  connectedCallback() {
    this.classList.add("modal", "drawer");

    // Render modal structure
    render(
      html`
        <div class="modal-overlay" data-close-modal></div>
        <div class="modal-container" role="dialog" aria-modal="true">
          <div class="modal-header">
            <h2>Filters</h2>
            <button
              class="btn btn-noborder close"
              aria-label="Close dialog"
              data-close-modal
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                stroke-width="2"
                stroke="currentColor"
                fill="none"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                <path d="M18 6l-12 12"></path>
                <path d="M6 6l12 12"></path>
              </svg>
            </button>
          </div>
          <div class="modal-body"></div>
        </div>
      `,
      this,
    );
    // Teleport filter content
    this.teleport();
    // Force close on turbo cache to restore content
    this.doClose = this.doClose.bind(this);
    document.addEventListener("turbo:before-cache", this.doClose);
    // Force reflow to make transform transition work
    this.getBoundingClientRect();
    // Add active class to start slide-in animation
    requestAnimationFrame(() => this.classList.add("active"));
    // Call super.init() after rendering to ensure elements are available
    super.init();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.teleportBack();
    document.removeEventListener("turbo:before-cache", this.doClose);
  }

  mapHeading(container, from, to) {
    const headings = container.querySelectorAll(from);
    headings.forEach((heading) => {
      const newHeading = document.createElement(to);
      newHeading.textContent = heading.textContent;
      heading.replaceWith(newHeading);
    });
  }

  teleport() {
    const content = this.querySelector(".modal-body");
    const sidePanel = document.querySelector(".side-panel");
    content.append(...sidePanel.children);
    this.mapHeading(content, "h2", "h3");
  }

  teleportBack() {
    const sidePanel = document.querySelector(".side-panel");
    const content = this.querySelector(".modal-body");
    sidePanel.append(...content.children);
    this.mapHeading(sidePanel, "h3", "h2");
  }

  doClose() {
    super.doClose();

    // Try restore focus to drawer trigger
    const restoreFocusElement =
      document.querySelector("ld-filter-drawer-trigger") || document.body;
    restoreFocusElement.focus({ focusVisible: isKeyboardActive() });
  }
}

customElements.define("ld-filter-drawer", FilterDrawer);
