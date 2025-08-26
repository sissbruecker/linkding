import { Behavior, registerBehavior } from "./index";
import { ModalBehavior } from "./modal";
import { isKeyboardActive } from "./focus-utils";

class FilterDrawerTriggerBehavior extends Behavior {
  constructor(element) {
    super(element);

    this.onClick = this.onClick.bind(this);

    element.addEventListener("click", this.onClick);
  }

  destroy() {
    this.element.removeEventListener("click", this.onClick);
  }

  onClick() {
    const modal = document.createElement("div");
    modal.classList.add("modal", "drawer", "filter-drawer");
    modal.setAttribute("ld-filter-drawer", "");
    modal.innerHTML = `
      <div class="modal-overlay"></div>
      <div class="modal-container" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h2>Filters</h2>
          <button class="btn btn-noborder close" aria-label="Close dialog">
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
    document.body.querySelector(".modals").appendChild(modal);
  }
}

class FilterDrawerBehavior extends ModalBehavior {
  init() {
    // Teleport content before creating focus trap, otherwise it will not detect
    // focusable content elements
    this.teleport();
    super.init();
    // Add active class to start slide-in animation
    this.element.classList.add("active");
  }

  destroy() {
    super.destroy();
    // Always close on destroy to restore drawer content to original location
    // before turbo caches DOM
    this.doClose();
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
    const content = this.element.querySelector(".content");
    const sidePanel = document.querySelector(".side-panel");
    content.append(...sidePanel.children);
    this.mapHeading(content, "h2", "h3");
  }

  teleportBack() {
    const sidePanel = document.querySelector(".side-panel");
    const content = this.element.querySelector(".content");
    sidePanel.append(...content.children);
    this.mapHeading(sidePanel, "h3", "h2");
  }

  doClose() {
    super.doClose();
    this.teleportBack();

    // Try restore focus to drawer trigger
    const restoreFocusElement =
      document.querySelector("[ld-filter-drawer-trigger]") || document.body;
    restoreFocusElement.focus({ focusVisible: isKeyboardActive() });
  }
}

registerBehavior("ld-filter-drawer-trigger", FilterDrawerTriggerBehavior);
registerBehavior("ld-filter-drawer", FilterDrawerBehavior);
