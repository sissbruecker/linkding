import { applyBehaviors, registerBehavior } from "./index";

class ModalBehavior {
  constructor(element) {
    const toggle = element;
    toggle.addEventListener("click", this.onToggleClick.bind(this));
    this.toggle = toggle;
  }

  async onToggleClick(event) {
    // Ignore Ctrl + click
    if (event.ctrlKey || event.metaKey) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();

    // Create modal either by teleporting existing content or fetching from URL
    const modal = this.toggle.hasAttribute("modal-content")
      ? this.createFromContent()
      : await this.createFromUrl();

    if (!modal) {
      return;
    }

    // Register close handlers
    const modalOverlay = modal.querySelector(".modal-overlay");
    const closeButton = modal.querySelector("button.close");
    modalOverlay.addEventListener("click", this.onClose.bind(this));
    closeButton.addEventListener("click", this.onClose.bind(this));

    document.body.append(modal);
    applyBehaviors(document.body);
    this.modal = modal;
  }

  async createFromUrl() {
    const url = this.toggle.getAttribute("modal-url");
    const modalHtml = await fetch(url).then((response) => response.text());
    const parser = new DOMParser();
    const doc = parser.parseFromString(modalHtml, "text/html");
    return doc.querySelector(".modal");
  }

  createFromContent() {
    const contentSelector = this.toggle.getAttribute("modal-content");
    const content = document.querySelector(contentSelector);
    if (!content) {
      return;
    }

    // Todo: make title configurable, only used for tag cloud for now
    const modal = document.createElement("div");
    modal.classList.add("modal", "active");
    modal.innerHTML = `
      <div class="modal-overlay" aria-label="Close"></div>
      <div class="modal-container">
        <div class="modal-header d-flex justify-between align-center">
          <div class="modal-title h5">Tags</div>
          <button class="close">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M18 6l-12 12"></path>
            <path d="M6 6l12 12"></path>
          </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="content"></div>
        </div>
      </div>
    `;

    const contentOwner = content.parentElement;
    const contentContainer = modal.querySelector(".content");
    contentContainer.append(content);
    this.content = content;
    this.contentOwner = contentOwner;

    return modal;
  }

  onClose() {
    // Teleport content back
    if (this.content && this.contentOwner) {
      this.contentOwner.append(this.content);
    }

    // Remove modal
    this.modal.classList.add("closing");
    this.modal.addEventListener("animationend", (event) => {
      if (event.animationName === "fade-out") {
        this.modal.remove();
      }
    });
  }
}

registerBehavior("ld-modal", ModalBehavior);
