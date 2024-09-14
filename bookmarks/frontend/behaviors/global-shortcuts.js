import { Behavior, registerBehavior } from "./index";

class GlobalShortcuts extends Behavior {
  constructor(element) {
    super(element);

    this.onKeyDown = this.onKeyDown.bind(this);
    document.addEventListener("keydown", this.onKeyDown);
  }

  destroy() {
    document.removeEventListener("keydown", this.onKeyDown);
  }

  onKeyDown(event) {
    // Skip if event occurred within an input element
    const targetNodeName = event.target.nodeName;
    const isInputTarget =
      targetNodeName === "INPUT" ||
      targetNodeName === "SELECT" ||
      targetNodeName === "TEXTAREA";

    if (isInputTarget) {
      return;
    }

    // Handle shortcuts for navigating bookmarks with arrow keys
    const isArrowUp = event.key === "ArrowUp";
    const isArrowDown = event.key === "ArrowDown";
    if (isArrowUp || isArrowDown) {
      event.preventDefault();

      // Detect current bookmark list item
      const path = event.composedPath();
      const currentItem = path.find(
        (item) => item.hasAttribute && item.hasAttribute("ld-bookmark-item"),
      );

      // Find next item
      let nextItem;
      if (currentItem) {
        nextItem = isArrowUp
          ? currentItem.previousElementSibling
          : currentItem.nextElementSibling;
      } else {
        // Select first item
        nextItem = document.querySelector("[ld-bookmark-item]");
      }
      // Focus first link
      if (nextItem) {
        nextItem.querySelector("a").focus();
      }
    }

    // Handle shortcut for toggling all notes
    if (event.key === "e") {
      const list = document.querySelector(".bookmark-list");
      if (list) {
        list.classList.toggle("show-notes");
      }
    }

    // Handle shortcut for focusing search input
    if (event.key === "s") {
      const searchInput = document.querySelector('input[type="search"]');

      if (searchInput) {
        searchInput.focus();
        event.preventDefault();
      }
    }

    // Handle shortcut for adding new bookmark
    if (event.key === "n") {
      window.location.assign("/bookmarks/new");
    }
  }
}

registerBehavior("ld-global-shortcuts", GlobalShortcuts);
