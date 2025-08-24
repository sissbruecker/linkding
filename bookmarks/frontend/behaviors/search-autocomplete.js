import { Behavior, registerBehavior } from "./index";
import "../components/SearchAutocomplete.js";

class SearchAutocomplete extends Behavior {
  constructor(element) {
    super(element);
    const input = element.querySelector("input");
    if (!input) {
      console.warn("SearchAutocomplete: input element not found");
      return;
    }

    const autocomplete = document.createElement("ld-search-autocomplete");
    autocomplete.name = "q";
    autocomplete.placeholder = input.getAttribute("placeholder") || "";
    autocomplete.value = input.value;
    autocomplete.linkTarget = input.dataset.linkTarget || "_blank";
    autocomplete.mode = input.dataset.mode || "";
    autocomplete.search = {
      user: input.dataset.user,
      shared: input.dataset.shared,
      unread: input.dataset.unread,
    };

    this.input = input;
    this.autocomplete = autocomplete;
    input.replaceWith(this.autocomplete);
  }

  destroy() {
    this.autocomplete.replaceWith(this.input);
  }
}

registerBehavior("ld-search-autocomplete", SearchAutocomplete);
