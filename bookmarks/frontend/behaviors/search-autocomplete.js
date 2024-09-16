import { Behavior, registerBehavior } from "./index";
import SearchAutoCompleteComponent from "../components/SearchAutoComplete.svelte";

class SearchAutocomplete extends Behavior {
  constructor(element) {
    super(element);
    const input = element.querySelector("input");
    if (!input) {
      console.warn("SearchAutocomplete: input element not found");
      return;
    }

    const container = document.createElement("div");

    new SearchAutoCompleteComponent({
      target: container,
      props: {
        name: "q",
        placeholder: input.getAttribute("placeholder") || "",
        value: input.value,
        linkTarget: input.dataset.linkTarget,
        mode: input.dataset.mode,
        search: {
          user: input.dataset.user,
          shared: input.dataset.shared,
          unread: input.dataset.unread,
        },
      },
    });

    this.input = input;
    this.autocomplete = container.firstElementChild;
    input.replaceWith(this.autocomplete);
  }

  destroy() {
    this.autocomplete.replaceWith(this.input);
  }
}

registerBehavior("ld-search-autocomplete", SearchAutocomplete);
