import { registerBehavior } from "./index";
import { isKeyboardActive } from "./focus-utils";
import { ModalBehavior } from "./modal";

class DetailsModalBehavior extends ModalBehavior {
  doClose() {
    super.doClose();

    // Navigate to close URL
    const closeUrl = this.element.dataset.closeUrl;
    Turbo.visit(closeUrl, {
      action: "replace",
      frame: "details-modal",
    });

    // Try restore focus to view details to view details link of respective bookmark
    const bookmarkId = this.element.dataset.bookmarkId;
    const restoreFocusElement =
      document.querySelector(
        `ul.bookmark-list li[data-bookmark-id='${bookmarkId}'] a.view-action`,
      ) ||
      document.querySelector("ul.bookmark-list") ||
      document.body;

    restoreFocusElement.focus({ focusVisible: isKeyboardActive() });
  }
}

registerBehavior("ld-details-modal", DetailsModalBehavior);
