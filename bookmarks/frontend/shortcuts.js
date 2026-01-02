document.addEventListener("keydown", (event) => {
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
    const items = [...document.querySelectorAll("ul.bookmark-list > li")];
    const path = event.composedPath();
    const currentItem = path.find((item) => items.includes(item));

    // Find next item
    let nextItem;
    if (currentItem) {
      nextItem = isArrowUp
        ? currentItem.previousElementSibling
        : currentItem.nextElementSibling;
    } else {
      // Select first item
      nextItem = items[0];
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
});
