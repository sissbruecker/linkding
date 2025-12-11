import { HeadlessElement } from "../utils/element.js";

class BookmarkPage extends HeadlessElement {
  init() {
    this.update = this.update.bind(this);
    this.onToggleNotes = this.onToggleNotes.bind(this);
    this.onToggleBulkEdit = this.onToggleBulkEdit.bind(this);
    this.onBulkActionChange = this.onBulkActionChange.bind(this);
    this.onToggleAll = this.onToggleAll.bind(this);
    this.onToggleBookmark = this.onToggleBookmark.bind(this);

    this.oldItems = [];
    this.update();
    document.addEventListener("bookmark-list-updated", this.update);
  }

  disconnectedCallback() {
    document.removeEventListener("bookmark-list-updated", this.update);
  }

  update() {
    const items = this.querySelectorAll("ul.bookmark-list > li");
    this.updateTooltips(items);
    this.updateNotesToggles(items, this.oldItems);
    this.updateBulkEdit(items, this.oldItems);
    this.oldItems = items;
  }

  updateTooltips(items) {
    // Add tooltip to title if it is truncated
    items.forEach((item) => {
      const titleAnchor = item.querySelector(".title > a");
      const titleSpan = titleAnchor.querySelector("span");
      if (titleSpan.offsetWidth > titleAnchor.offsetWidth) {
        titleAnchor.dataset.tooltip = titleSpan.textContent;
      } else {
        delete titleAnchor.dataset.tooltip;
      }
    });
  }

  updateNotesToggles(items, oldItems) {
    oldItems.forEach((oldItem) => {
      const oldToggle = oldItem.querySelector(".toggle-notes");
      if (oldToggle) {
        oldToggle.removeEventListener("click", this.onToggleNotes);
      }
    });

    items.forEach((item) => {
      const notesToggle = item.querySelector(".toggle-notes");
      if (notesToggle) {
        notesToggle.addEventListener("click", this.onToggleNotes);
      }
    });
  }

  onToggleNotes(event) {
    event.preventDefault();
    event.stopPropagation();
    event.target.closest("li").classList.toggle("show-notes");
  }

  updateBulkEdit() {
    if (this.hasAttribute("no-bulk-edit")) {
      return;
    }

    // Remove existing listeners
    this.activeToggle?.removeEventListener("click", this.onToggleBulkEdit);
    this.actionSelect?.removeEventListener("change", this.onBulkActionChange);
    this.allCheckbox?.removeEventListener("change", this.onToggleAll);
    this.bookmarkCheckboxes?.forEach((checkbox) => {
      checkbox.removeEventListener("change", this.onToggleBookmark);
    });

    // Re-query elements
    this.activeToggle = this.querySelector(".bulk-edit-active-toggle");
    this.actionSelect = this.querySelector("select[name='bulk_action']");
    this.allCheckbox = this.querySelector(".bulk-edit-checkbox.all input");
    this.bookmarkCheckboxes = Array.from(
      this.querySelectorAll(".bulk-edit-checkbox:not(.all) input"),
    );
    this.selectAcross = this.querySelector("label.select-across");
    this.executeButton = this.querySelector("button[name='bulk_execute']");

    // Add listeners
    this.activeToggle.addEventListener("click", this.onToggleBulkEdit);
    this.actionSelect.addEventListener("change", this.onBulkActionChange);
    this.allCheckbox.addEventListener("change", this.onToggleAll);
    this.bookmarkCheckboxes.forEach((checkbox) => {
      checkbox.addEventListener("change", this.onToggleBookmark);
    });

    // Reset checkbox states
    this.allCheckbox.checked = false;
    this.bookmarkCheckboxes.forEach((checkbox) => {
      checkbox.checked = false;
    });
    this.updateSelectAcross(false);
    this.updateExecuteButton();

    // Update total number of bookmarks
    const totalHolder = this.querySelector("[data-bookmarks-total]");
    const total = totalHolder?.dataset.bookmarksTotal || 0;
    const totalSpan = this.selectAcross.querySelector("span.total");
    totalSpan.textContent = total;
  }

  onToggleBulkEdit() {
    this.classList.toggle("active");
  }

  onBulkActionChange() {
    this.dataset.bulkAction = this.actionSelect.value;
  }

  onToggleAll() {
    const allChecked = this.allCheckbox.checked;
    this.bookmarkCheckboxes.forEach((checkbox) => {
      checkbox.checked = allChecked;
    });
    this.updateSelectAcross(allChecked);
    this.updateExecuteButton();
  }

  onToggleBookmark() {
    const allChecked = this.bookmarkCheckboxes.every((checkbox) => {
      return checkbox.checked;
    });
    this.allCheckbox.checked = allChecked;
    this.updateSelectAcross(allChecked);
    this.updateExecuteButton();
  }

  updateSelectAcross(allChecked) {
    if (allChecked) {
      this.selectAcross.classList.remove("d-none");
    } else {
      this.selectAcross.classList.add("d-none");
      this.selectAcross.querySelector("input").checked = false;
    }
  }

  updateExecuteButton() {
    const anyChecked = this.bookmarkCheckboxes.some((checkbox) => {
      return checkbox.checked;
    });
    this.executeButton.disabled = !anyChecked;
  }
}

customElements.define("ld-bookmark-page", BookmarkPage);
