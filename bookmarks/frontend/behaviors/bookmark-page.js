import { ApiClient } from "../api";
import { Behavior, registerBehavior } from "./index";

class BookmarkItem extends Behavior {
  constructor(element) {
    super(element);

    // Toggle notes
    const notesToggle = element.querySelector(".toggle-notes");
    if (notesToggle) {
      notesToggle.addEventListener("click", this.onToggleNotes.bind(this));
    }

    // Add tooltip to title if it is truncated
    const titleAnchor = element.querySelector(".title > a");
    const titleSpan = titleAnchor.querySelector("span");
    requestAnimationFrame(() => {
      if (titleSpan.offsetWidth > titleAnchor.offsetWidth) {
        titleAnchor.dataset.tooltip = titleSpan.textContent;
      }
    });

    const csrftoken = element.querySelector("[name=csrfmiddlewaretoken]").value;
    const id = element.querySelector("[name=bookmark_id]").value;
    const apiBaseUrl = document.documentElement.dataset.apiBaseUrl || "";
    const apiClient = new ApiClient(apiBaseUrl, csrftoken);
    titleAnchor.addEventListener("click", async () => {
      await apiClient.markBookmarkAccessed(id);
    });
  }

  onToggleNotes(event) {
    event.preventDefault();
    event.stopPropagation();
    this.element.classList.toggle("show-notes");
  }
}

registerBehavior("ld-bookmark-item", BookmarkItem);
