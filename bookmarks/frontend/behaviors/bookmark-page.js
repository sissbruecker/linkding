import { registerBehavior, swap } from "./index";

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
      swap(this.bookmarkList, bookmarkListHtml);
      swap(this.tagCloud, tagCloudHtml);

      // Dispatch list updated event
      const listElement = this.bookmarkList.querySelector(
        "ul[data-bookmarks-total]",
      );
      const bookmarksTotal =
        (listElement && listElement.dataset.bookmarksTotal) || 0;

      this.bookmarkList.dispatchEvent(
        new CustomEvent("bookmark-list-updated", {
          bubbles: true,
          detail: { bookmarksTotal },
        }),
      );
    });
  }
}

registerBehavior("ld-bookmark-page", BookmarkPage);

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
    // Enable show more if description is truncated.
    const showMoreBtn = this.element.querySelector(".show-more.btn")
    const showMore = this.element.querySelector(".show-more")
    showMoreBtn.addEventListener("click", this.onToggleMore.bind(this))
    const description = this.element.querySelector(".description")
    const text = this.element.querySelector(".description span")
    if (text.offsetHeight > description.offsetHeight) {
      showMore.classList.remove("hidden")
    }
  }

  onToggleMore(event) {
    event.preventDefault();
    event.stopPropagation();
    const desc = this.element.querySelector(".description")
    const btn = this.element.querySelector(".show-more.btn")
    if (btn.textContent == "Show more") {
      btn.textContent = "Show less"
    } else {
      btn.textContent = "Show more"
    }
    desc.classList.toggle("desc-no-overflow")
  }

  onToggleNotes(event) {
    event.preventDefault();
    event.stopPropagation();
    this.element.classList.toggle("show-notes");
  }
}

registerBehavior("ld-bookmark-item", BookmarkItem);
