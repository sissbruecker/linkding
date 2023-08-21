class BulkEdit extends HTMLElement {
  constructor() {
    super();
    this.active = false;
  }

  get allCheckbox() {
    return this.querySelector("ld-bulk-edit-checkbox[all] input");
  }

  get bookmarkCheckboxes() {
    return [...this.querySelectorAll("ld-bulk-edit-checkbox:not([all]) input")];
  }

  connectedCallback() {
    this.addEventListener(
      "bulk-edit-toggle-active",
      this.onToggleActive.bind(this),
    );
    this.addEventListener("bulk-edit-toggle-all", this.onToggleAll.bind(this));
    this.addEventListener(
      "bulk-edit-toggle-bookmark",
      this.onToggleBookmark.bind(this),
    );
  }

  onToggleActive() {
    this.active = !this.active;
    if (this.active) {
      this.classList.add("active", "activating");
      setTimeout(() => {
        this.classList.remove("activating");
      }, 500);
    } else {
      this.classList.remove("active");
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

  reset() {
    this.allCheckbox.checked = false;
    this.bookmarkCheckboxes.forEach((checkbox) => {
      checkbox.checked = false;
    });
  }
}

class BulkEditActiveToggle extends HTMLElement {
  connectedCallback() {
    const button = this.querySelector("button");
    button.addEventListener("click", this.onClick.bind(this));
  }

  onClick() {
    this.dispatchEvent(
      new CustomEvent("bulk-edit-toggle-active", { bubbles: true }),
    );
  }
}

class BulkEditCheckbox extends HTMLElement {
  connectedCallback() {
    const checkbox = this.querySelector("input");
    checkbox.addEventListener("change", this.onChange.bind(this));
  }

  onChange() {
    const type = this.hasAttribute("all") ? "all" : "bookmark";
    this.dispatchEvent(
      new CustomEvent(`bulk-edit-toggle-${type}`, { bubbles: true }),
    );
  }
}

customElements.define("ld-bulk-edit", BulkEdit);
customElements.define("ld-bulk-edit-active-toggle", BulkEditActiveToggle);
customElements.define("ld-bulk-edit-checkbox", BulkEditCheckbox);

class BookmarkPage extends HTMLElement {
  connectedCallback() {
    this.form = this.querySelector("form.bookmark-actions");
    this.form.addEventListener("submit", this.onFormSubmit.bind(this));

    this.bulkEdit = this.querySelector("ld-bulk-edit");
    this.bookmarkList = this.querySelector(".bookmark-list-container");
    this.tagCloud = this.querySelector(".tag-cloud-container");

    document.addEventListener("keydown", this.onKeyDown.bind(this));
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

    if (this.bulkEdit) {
      this.bulkEdit.reset();
    }
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
      const currentItem = path.find((item) => item instanceof BookmarkItem);

      // Find next item
      let nextItem;
      if (currentItem) {
        nextItem = isArrowUp
          ? currentItem.previousElementSibling
          : currentItem.nextElementSibling;
      } else {
        // Select first item
        nextItem = document.querySelector("ld-bookmark-item");
      }
      // Focus first link
      if (nextItem) {
        nextItem.querySelector("a").focus();
      }
    }

    // Handle shortcut for toggling all notes
    if (event.key === "e") {
      const list = document.querySelector(".bookmark-list");
      list.classList.toggle("show-notes");
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

  async refresh() {
    const queryParams = window.location.search;
    const bookmarkListUrl = this.getAttribute("bookmark-list-url");
    const tagCloudUrl = this.getAttribute("tag-cloud-url");
    Promise.all([
      fetch(`${bookmarkListUrl}${queryParams}`).then((response) =>
        response.text(),
      ),
      fetch(`${tagCloudUrl}${queryParams}`).then((response) => response.text()),
    ]).then(([bookmarkListHtml, tagCloudHtml]) => {
      this.bookmarkList.innerHTML = bookmarkListHtml;
      this.tagCloud.innerHTML = tagCloudHtml;

      linkding.swap(this.bookmarkList, bookmarkListHtml);
      linkding.swap(this.tagCloud, tagCloudHtml);
    });
  }
}

customElements.define("ld-bookmark-page", BookmarkPage);

class BookmarkItem extends HTMLElement {
  connectedCallback() {
    this.bookmark = this.querySelector("li");

    const notesToggle = this.querySelector(".toggle-notes");
    if (notesToggle) {
      notesToggle.addEventListener("click", this.onToggleNotes.bind(this));
    }
  }

  onToggleNotes(event) {
    event.preventDefault();
    event.stopPropagation();
    this.bookmark.classList.toggle("show-notes");
  }
}

customElements.define("ld-bookmark-item", BookmarkItem);
