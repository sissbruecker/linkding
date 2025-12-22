import { registerBehavior } from "./index";
import { isKeyboardActive, setAfterPageLoadFocusTarget } from "./focus-utils";
import { ModalBehavior } from "./modal";

class DetailsModalBehavior extends ModalBehavior {
  doClose() {
    super.doClose();

    // Try restore focus to view details to view details link of respective bookmark
    const bookmarkId = this.element.dataset.bookmarkId;
    setAfterPageLoadFocusTarget(
      `ul.bookmark-list li[data-bookmark-id='${bookmarkId}'] a.view-action`,
    );
  }
}

registerBehavior("ld-details-modal", DetailsModalBehavior);
