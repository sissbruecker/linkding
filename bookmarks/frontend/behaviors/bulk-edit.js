import { registerBehavior } from "./index";

class BulkEdit {
  constructor(element) {
    this.element = element;
    this.active = false;
    this.actionSelect = element.querySelector("select[name='bulk_action']");
    this.bulkActions = element.querySelector(".bulk-edit-actions");

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

  onActionSelected() {
    const action = this.actionSelect.value;

    if (action === "bulk_tag" || action === "bulk_untag") {
      this.bulkActions.classList.add("bulk-tag-action");
    } else {
      this.bulkActions.classList.remove("bulk-tag-action");
    }
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

registerBehavior("ld-bulk-edit", BulkEdit);
registerBehavior("ld-bulk-edit-active-toggle", BulkEditActiveToggle);
registerBehavior("ld-bulk-edit-checkbox", BulkEditCheckbox);
