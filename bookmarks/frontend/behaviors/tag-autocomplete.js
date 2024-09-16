import { Behavior, registerBehavior } from "./index";
import TagAutoCompleteComponent from "../components/TagAutocomplete.svelte";

class TagAutocomplete extends Behavior {
  constructor(element) {
    super(element);
    const input = element.querySelector("input");
    if (!input) {
      console.warn("TagAutocomplete: input element not found");
      return;
    }

    const container = document.createElement("div");

    new TagAutoCompleteComponent({
      target: container,
      props: {
        id: input.id,
        name: input.name,
        value: input.value,
        placeholder: input.getAttribute("placeholder") || "",
        variant: input.getAttribute("variant"),
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

registerBehavior("ld-tag-autocomplete", TagAutocomplete);
