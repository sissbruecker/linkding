class BulkEdit {
  constructor(element) {
    this.element = element;
    this.active = false;

    element.addEventListener(
      "bulk-edit-toggle-active",
      this.onToggleActive.bind(this),
    );
    element.addEventListener(
      "bulk-edit-toggle-all",
      this.onToggleAll.bind(this),
    );
    element.addEventListener(
      "bulk-edit-toggle-bookmark",
      this.onToggleBookmark.bind(this),
    );
    element.addEventListener(
      "bookmark-list-updated",
      this.onListUpdated.bind(this),
    );
  }

  get allCheckbox() {
    return this.element.querySelector("[ld-bulk-edit-checkbox][all] input");
  }

  get bookmarkCheckboxes() {
    return [
      ...this.element.querySelectorAll(
        "[ld-bulk-edit-checkbox]:not([all]) input",
      ),
    ];
  }

  onToggleActive() {
    this.active = !this.active;
    if (this.active) {
      this.element.classList.add("active", "activating");
      setTimeout(() => {
        this.element.classList.remove("activating");
      }, 500);
    } else {
      this.element.classList.remove("active");
    }
  }

  onToggleBookmark() {
    this.allCheckbox.checked = this.bookmarkCheckboxes.every((checkbox) => {
      return checkbox.checked;
    });
  }

  onToggleAll() {
    const checked = this.allCheckbox.checked;
    this.bookmarkCheckboxes.forEach((checkbox) => {
      checkbox.checked = checked;
    });
  }

  onListUpdated() {
    this.allCheckbox.checked = false;
    this.bookmarkCheckboxes.forEach((checkbox) => {
      checkbox.checked = false;
    });
  }
}

class BulkEditActiveToggle {
  constructor(element) {
    this.element = element;
    element.addEventListener("click", this.onClick.bind(this));
  }

  onClick() {
    this.element.dispatchEvent(
      new CustomEvent("bulk-edit-toggle-active", { bubbles: true }),
    );
  }
}

class BulkEditCheckbox {
  constructor(element) {
    this.element = element;
    element.addEventListener("change", this.onChange.bind(this));
  }

  onChange() {
    const type = this.element.hasAttribute("all") ? "all" : "bookmark";
    this.element.dispatchEvent(
      new CustomEvent(`bulk-edit-toggle-${type}`, { bubbles: true }),
    );
  }
}

linkding.registerBehavior("ld-bulk-edit", BulkEdit);
linkding.registerBehavior("ld-bulk-edit-active-toggle", BulkEditActiveToggle);
linkding.registerBehavior("ld-bulk-edit-checkbox", BulkEditCheckbox);

class BookmarkPage {
  constructor(element) {
    this.element = element;
    this.form = element.querySelector("form.bookmark-actions");
    this.form.addEventListener("submit", this.onFormSubmit.bind(this));

    this.bookmarkList = element.querySelector(".bookmark-list-container");
    this.tagCloud = element.querySelector(".tag-cloud-container");
  }

  async onFormSubmit(event) {
    event.preventDefault();

    const url = this.form.action;
    const formData = new FormData(this.form);
    formData.append(event.submitter.name, event.submitter.value);

    await fetch(url, {
      method: "POST",
      body: formData,
      redirect: "manual", // ignore redirect
    });
    await this.refresh();
  }

  async refresh() {
    const query = window.location.search;
    const bookmarksUrl = this.element.getAttribute("bookmarks-url");
    const tagsUrl = this.element.getAttribute("tags-url");
    Promise.all([
      fetch(`${bookmarksUrl}${query}`).then((response) => response.text()),
      fetch(`${tagsUrl}${query}`).then((response) => response.text()),
    ]).then(([bookmarkListHtml, tagCloudHtml]) => {
      linkding.swap(this.bookmarkList, bookmarkListHtml);
      linkding.swap(this.tagCloud, tagCloudHtml);

      this.bookmarkList.dispatchEvent(
        new CustomEvent("bookmark-list-updated", { bubbles: true }),
      );
    });
  }
}

linkding.registerBehavior("ld-bookmark-page", BookmarkPage);

class BookmarkItem {
  constructor(element) {
    this.element = element;

    const notesToggle = element.querySelector(".toggle-notes");
    if (notesToggle) {
      notesToggle.addEventListener("click", this.onToggleNotes.bind(this));
    }
  }

  onToggleNotes(event) {
    event.preventDefault();
    event.stopPropagation();
    this.element.classList.toggle("show-notes");
  }
}

linkding.registerBehavior("ld-bookmark-item", BookmarkItem);

class GlobalShortcuts {
  constructor() {
    document.addEventListener("keydown", this.onKeyDown.bind(this));
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

linkding.registerBehavior("ld-global-shortcuts", GlobalShortcuts);
