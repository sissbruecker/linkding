class BulkEdit extends HTMLElement {
  constructor() {
    super();
    this.editing = false;
  }

  get allCheckbox() {
    return this.querySelector("ld-bulk-edit-checkbox[type='all'] input");
  }

  get bookmarkCheckboxes() {
    return [
      ...this.querySelectorAll("ld-bulk-edit-checkbox[type='single'] input"),
    ];
  }

  connectedCallback() {
    this.addEventListener(
      "bulk-edit-toggle-mode",
      this.onToggleMode.bind(this),
    );
    this.addEventListener("bulk-edit-toggle-all", this.onToggleAll.bind(this));
    this.addEventListener(
      "bulk-edit-toggle-single",
      this.onToggleSingle.bind(this),
    );
    this.addEventListener(
      "bookmark-actions-form-submit",
      this.onFormSubmit.bind(this),
    );
  }

  onToggleMode() {
    this.editing = !this.editing;
    if (this.editing) {
      this.classList.add("editing", "opening");
      setTimeout(() => {
        this.classList.remove("opening");
      }, 500);
    } else {
      this.classList.remove("editing");
    }
  }

  onToggleSingle() {
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

  onFormSubmit() {
    this.allCheckbox.checked = false;
    this.bookmarkCheckboxes.forEach((checkbox) => {
      checkbox.checked = false;
    });
  }
}

class BulkEditToggle extends HTMLElement {
  connectedCallback() {
    const button = this.querySelector("button");
    button.addEventListener("click", this.onClick.bind(this));
  }

  onClick() {
    this.dispatchEvent(
      new CustomEvent("bulk-edit-toggle-mode", { bubbles: true }),
    );
  }
}

class BulkEditCheckbox extends HTMLElement {
  connectedCallback() {
    const checkbox = this.querySelector("input");
    checkbox.addEventListener("change", this.onChange.bind(this));
  }

  onChange() {
    const type = this.getAttribute("type") || "single";
    this.dispatchEvent(
      new CustomEvent("bulk-edit-toggle-" + type, { bubbles: true }),
    );
  }
}

customElements.define("ld-bulk-edit", BulkEdit);
customElements.define("ld-bulk-edit-toggle", BulkEditToggle);
customElements.define("ld-bulk-edit-checkbox", BulkEditCheckbox);

(function () {
  function setupListNavigation() {
    // Add logic for navigating bookmarks with arrow keys
    document.addEventListener("keydown", (event) => {
      // Skip if event occurred within an input element
      // or does not use arrow keys
      const targetNodeName = event.target.nodeName;
      const isInputTarget =
        targetNodeName === "INPUT" ||
        targetNodeName === "SELECT" ||
        targetNodeName === "TEXTAREA";
      const isArrowUp = event.key === "ArrowUp";
      const isArrowDown = event.key === "ArrowDown";

      if (isInputTarget || !(isArrowUp || isArrowDown)) {
        return;
      }
      event.preventDefault();

      // Detect current bookmark list item
      const path = event.composedPath();
      const currentItem = path.find(
        (item) =>
          item.hasAttribute && item.hasAttribute("data-is-bookmark-item"),
      );

      // Find next item
      let nextItem;
      if (currentItem) {
        nextItem = isArrowUp
          ? currentItem.previousElementSibling
          : currentItem.nextElementSibling;
      } else {
        // Select first item
        nextItem = document.querySelector("li[data-is-bookmark-item]");
      }
      // Focus first link
      if (nextItem) {
        nextItem.querySelector("a").focus();
      }
    });
  }

  function setupNotes() {
    // Shortcut for toggling all notes
    document.addEventListener("keydown", function (event) {
      // Filter for shortcut key
      if (event.key !== "e") return;
      // Skip if event occurred within an input element
      const targetNodeName = event.target.nodeName;
      const isInputTarget =
        targetNodeName === "INPUT" ||
        targetNodeName === "SELECT" ||
        targetNodeName === "TEXTAREA";

      if (isInputTarget) return;

      const list = document.querySelector(".bookmark-list");
      list.classList.toggle("show-notes");
    });

    // Toggle notes for single bookmark
    const bookmarks = document.querySelectorAll(".bookmark-list li");
    bookmarks.forEach((bookmark) => {
      const toggleButton = bookmark.querySelector(".toggle-notes");
      if (toggleButton) {
        toggleButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          bookmark.classList.toggle("show-notes");
        });
      }
    });
  }

  function setupPartialUpdate() {
    // Avoid full page reload and losing scroll position when triggering
    // bookmark actions and only do partial updates of the bookmark list and tag
    // cloud
    const form = document.querySelector("form.bookmark-actions");
    const bookmarkListContainer = document.querySelector(
      ".bookmark-list-container",
    );
    const tagCloudContainer = document.querySelector(".tag-cloud-container");
    if (!form || !bookmarkListContainer || !tagCloudContainer) {
      return;
    }

    form.addEventListener("submit", async function (event) {
      const url = form.action;
      const formData = new FormData(form, event.submitter);

      event.preventDefault();
      await fetch(url, {
        method: "POST",
        body: formData,
        redirect: "manual", // ignore redirect
      });
      form.dispatchEvent(
        new CustomEvent("bookmark-actions-form-submit", { bubbles: true }),
      );

      const queryParams = window.location.search;
      Promise.all([
        fetch(`/bookmarks/partials/bookmark-list${queryParams}`).then(
          (response) => response.text(),
        ),
        fetch(`/bookmarks/partials/tag-cloud${queryParams}`).then((response) =>
          response.text(),
        ),
      ]).then(([bookmarkListHtml, tagCloudHtml]) => {
        bookmarkListContainer.innerHTML = bookmarkListHtml;
        tagCloudContainer.innerHTML = tagCloudHtml;
      });
    });
  }

  setupListNavigation();
  setupNotes();
  setupPartialUpdate();
})();
