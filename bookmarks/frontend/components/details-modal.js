import { setAfterPageLoadFocusTarget } from "../utils/focus.js";
import { Modal } from "./modal.js";

class DetailsModal extends Modal {
  doClose() {
    super.doClose();

    // Try restore focus to view details to view details link of respective bookmark
    const bookmarkId = this.dataset.bookmarkId;
    setAfterPageLoadFocusTarget(
      `ul.bookmark-list li[data-bookmark-id='${bookmarkId}'] a.view-action`,
    );
  }
}

customElements.define("ld-details-modal", DetailsModal);
