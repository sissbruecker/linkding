import { Behavior, registerBehavior } from "./index";
import TagAutoCompleteComponent from "../components/TagAutocomplete.svelte";
import { ApiClient } from "../api";

class TagAutocomplete extends Behavior {
  constructor(element) {
    super(element);
    const input = element.querySelector("input");
    if (!input) {
      console.warning("TagAutocomplete: input element not found");
      return;
    }

    const container = document.createElement("div");
    const apiBaseUrl = document.documentElement.dataset.apiBaseUrl || "";
    const apiClient = new ApiClient(apiBaseUrl);

    new TagAutoCompleteComponent({
      target: container,
      props: {
        id: input.id,
        name: input.name,
        value: input.value,
        placeholder: input.getAttribute("placeholder") || "",
        apiClient: apiClient,
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
