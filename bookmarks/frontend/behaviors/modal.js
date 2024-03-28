import { registerBehavior } from "./index";

class ModalBehavior {
  constructor(element) {
    this.modal = element;

    // Register close handlers
    const modalOverlay = element.querySelector(".modal-overlay");
    const closeButton = element.querySelector(".btn.close");
    modalOverlay.addEventListener("click", this.onClose.bind(this));
    closeButton.addEventListener("click", this.onClose.bind(this));
  }

  onClose() {
    // Remove modal
    this.modal.remove();
  }
}

registerBehavior("ld-modal", ModalBehavior);

class TagModalBehavior {
  constructor(element) {
    const toggle = element;
    toggle.addEventListener("click", this.onToggleClick.bind(this));
    this.toggle = toggle;
  }

  onToggleClick() {
    const contentSelector = this.toggle.getAttribute("modal-content");
    const content = document.querySelector(contentSelector);
    if (!content) {
      return;
    }

    // Create modal
    const modal = document.createElement("div");
    modal.classList.add("modal", "active");
    modal.innerHTML = `
      <div class="modal-overlay" aria-label="Close"></div>
      <div class="modal-container">
        <div class="modal-header d-flex justify-between align-center">
          <div class="modal-title h5">Tags</div>
          <button class="btn btn-link close">
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

    // Teleport content element
    const contentOwner = content.parentElement;
    const contentContainer = modal.querySelector(".content");
    contentContainer.append(content);
    this.content = content;
    this.contentOwner = contentOwner;

    // Register close handlers
    const modalOverlay = modal.querySelector(".modal-overlay");
    const closeButton = modal.querySelector(".btn.close");
    modalOverlay.addEventListener("click", this.onClose.bind(this));
    closeButton.addEventListener("click", this.onClose.bind(this));

    document.body.append(modal);
    this.modal = modal;
  }

  onClose() {
    // Teleport content back
    this.contentOwner.append(this.content);

    // Remove modal
    this.modal.remove();
  }
}

registerBehavior("ld-tag-modal", TagModalBehavior);
