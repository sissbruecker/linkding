import { Behavior, registerBehavior } from "./index";
import "../components/TagAutocomplete.js";

class TagAutocomplete extends Behavior {
  constructor(element) {
    super(element);
    const input = element.querySelector("input");
    if (!input) {
      console.warn("TagAutocomplete: input element not found");
      return;
    }

    const autocomplete = document.createElement("ld-tag-autocomplete");
    autocomplete.id = input.id;
    autocomplete.name = input.name;
    autocomplete.value = input.value;
    autocomplete.placeholder = input.getAttribute("placeholder") || "";
    autocomplete.ariaDescribedBy = input.getAttribute("aria-describedby") || "";
    autocomplete.variant = input.getAttribute("variant") || "default";

    this.input = input;
    this.autocomplete = autocomplete;
    input.replaceWith(this.autocomplete);
  }

  destroy() {
    this.autocomplete.replaceWith(this.input);
  }
}

registerBehavior("ld-tag-autocomplete", TagAutocomplete);
