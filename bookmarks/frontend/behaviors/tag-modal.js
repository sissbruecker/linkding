import { Behavior, registerBehavior } from "./index";
import { ModalBehavior } from "./modal";
import { isKeyboardActive } from "./focus-utils";

class TagModalTriggerBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.onClick = this.onClick.bind(this);

    element.addEventListener("click", this.onClick);
  }

  destroy() {
    this.element.removeEventListener("click", this.onClick);
  }

  onClick() {
    // Creates a new modal and teleports the tag cloud into it
    const modal = document.createElement("div");
    modal.classList.add("modal", "drawer", "side-panel");
    modal.setAttribute("ld-tag-modal", "");
    modal.innerHTML = `
      <div class="modal-overlay"></div>
      <div class="modal-container" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h2>Tags</h2>
          <button class="close" aria-label="Close dialog">
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
    modal.addEventListener("modal:close", this.onClose);

    modal.tagCloud = document.querySelector(".tag-cloud");
    modal.tagCloudContainer = modal.tagCloud.parentElement;

    const content = modal.querySelector(".content");
    content.appendChild(modal.tagCloud);

    document.body.querySelector(".modals").appendChild(modal);
  }
}

class TagModalBehavior extends ModalBehavior {
  constructor(element) {
    super(element);
    // Add active class to start slide-in animation
    this.element.classList.add("active");
  }

  destroy() {
    super.destroy();
    // Always close on destroy to restore tag cloud to original parent before
    // turbo caches DOM
    this.doClose();
  }

  doClose() {
    super.doClose();

    // Restore tag cloud to original parent
    this.element.tagCloudContainer.appendChild(this.element.tagCloud);

    // Try restore focus to tag cloud trigger
    const restoreFocusElement =
      document.querySelector("[ld-tag-modal-trigger]") || document.body;
    restoreFocusElement.focus({ focusVisible: isKeyboardActive() });
  }
}

registerBehavior("ld-tag-modal-trigger", TagModalTriggerBehavior);
registerBehavior("ld-tag-modal", TagModalBehavior);
