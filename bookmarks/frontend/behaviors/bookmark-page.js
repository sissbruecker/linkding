import { registerBehavior } from "./index";

class BookmarkItem {
  constructor(element) {
    this.element = element;

    // Toggle notes
    const notesToggle = element.querySelector(".toggle-notes");
    if (notesToggle) {
      notesToggle.addEventListener("click", this.onToggleNotes.bind(this));
    }

    // Add tooltip to title if it is truncated
    const titleAnchor = element.querySelector(".title > a");
    const titleSpan = titleAnchor.querySelector("span");
    if (titleSpan.offsetWidth > titleAnchor.offsetWidth) {
      titleAnchor.dataset.tooltip = titleSpan.textContent;
    }
  }

  onToggleNotes(event) {
    event.preventDefault();
    event.stopPropagation();
    this.element.classList.toggle("show-notes");
  }
}

registerBehavior("ld-bookmark-item", BookmarkItem);
