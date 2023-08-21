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

      this.bookmarkList.dispatchEvent(
        new CustomEvent("bookmark-list-updated", { bubbles: true }),
      );
    });
  }
}

registerBehavior("ld-bookmark-page", BookmarkPage);

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

registerBehavior("ld-bookmark-item", BookmarkItem);
