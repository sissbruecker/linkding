import { Behavior, registerBehavior } from "./index";

class BookmarkItem extends Behavior {
  constructor(element) {
    super(element);

    // Toggle notes
    this.onToggleNotes = this.onToggleNotes.bind(this);
    this.notesToggle = element.querySelector(".toggle-notes");
    if (this.notesToggle) {
      this.notesToggle.addEventListener("click", this.onToggleNotes);
    }

    // Add tooltip to title if it is truncated
    const titleAnchor = element.querySelector(".title > a");
    const titleSpan = titleAnchor.querySelector("span");
    requestAnimationFrame(() => {
      if (titleSpan.offsetWidth > titleAnchor.offsetWidth) {
        titleAnchor.dataset.tooltip = titleSpan.textContent;
      }
    });
  }

  destroy() {
    if (this.notesToggle) {
      this.notesToggle.removeEventListener("click", this.onToggleNotes);
    }
  }

  onToggleNotes(event) {
    event.preventDefault();
    event.stopPropagation();
    this.element.classList.toggle("show-notes");
  }
}

registerBehavior("ld-bookmark-item", BookmarkItem);
