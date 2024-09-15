import { Behavior, registerBehavior } from "./index";

class TagModalBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.onClick = this.onClick.bind(this);
    this.onClose = this.onClose.bind(this);

    element.addEventListener("click", this.onClick);
  }

  destroy() {
    this.onClose();
    this.element.removeEventListener("click", this.onClick);
  }

  onClick() {
    const modal = document.createElement("div");
    modal.classList.add("modal", "active");
    modal.innerHTML = `
      <div class="modal-overlay" aria-label="Close"></div>
      <div class="modal-container">
        <div class="modal-header">
          <h2>Tags</h2>
          <button class="close" aria-label="Close">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" stroke-width="2"
                 stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
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

    const tagCloud = document.querySelector(".tag-cloud");
    const tagCloudContainer = tagCloud.parentElement;

    const content = modal.querySelector(".content");
    content.appendChild(tagCloud);

    const overlay = modal.querySelector(".modal-overlay");
    const closeButton = modal.querySelector(".close");
    overlay.addEventListener("click", this.onClose);
    closeButton.addEventListener("click", this.onClose);

    this.modal = modal;
    this.tagCloud = tagCloud;
    this.tagCloudContainer = tagCloudContainer;
    document.body.appendChild(modal);
  }

  onClose() {
    if (!this.modal) {
      return;
    }

    this.modal.remove();
    this.tagCloudContainer.appendChild(this.tagCloud);
  }
}

registerBehavior("ld-tag-modal", TagModalBehavior);
