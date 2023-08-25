import { registerBehavior } from "./index";

class BulkEdit {
  constructor(element) {
    this.element = element;
    this.active = false;
    this.actionSelect = element.querySelector("select[name='bulk_action']");
    this.tagAutoComplete = element.querySelector(".tag-autocomplete");
    this.selectAcross = element.querySelector("label.select-across");

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

    this.actionSelect.addEventListener(
      "change",
      this.onActionSelected.bind(this),
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
    const allChecked = this.bookmarkCheckboxes.every((checkbox) => {
      return checkbox.checked;
    });
    this.allCheckbox.checked = allChecked;
    this.updateSelectAcross(allChecked);
  }

  onToggleAll() {
    const allChecked = this.allCheckbox.checked;
    this.bookmarkCheckboxes.forEach((checkbox) => {
      checkbox.checked = allChecked;
    });
    this.updateSelectAcross(allChecked);
  }

  onActionSelected() {
    const action = this.actionSelect.value;

    if (action === "bulk_tag" || action === "bulk_untag") {
      this.tagAutoComplete.classList.remove("d-none");
    } else {
      this.tagAutoComplete.classList.add("d-none");
    }
  }

  onListUpdated(event) {
    // Reset checkbox states
    this.reset();

    // Update total number of bookmarks
    const total = event.detail.bookmarksTotal;
    const totalSpan = this.selectAcross.querySelector("span.total");
    totalSpan.textContent = total;
  }

  updateSelectAcross(allChecked) {
    if (allChecked) {
      this.selectAcross.classList.remove("d-none");
    } else {
      this.selectAcross.classList.add("d-none");
      this.selectAcross.querySelector("input").checked = false;
    }
  }

  reset() {
    this.allCheckbox.checked = false;
    this.bookmarkCheckboxes.forEach((checkbox) => {
      checkbox.checked = false;
    });
    this.updateSelectAcross(false);
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

registerBehavior("ld-bulk-edit", BulkEdit);
registerBehavior("ld-bulk-edit-active-toggle", BulkEditActiveToggle);
registerBehavior("ld-bulk-edit-checkbox", BulkEditCheckbox);
