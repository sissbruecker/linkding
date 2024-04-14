import { Behavior, registerBehavior } from "./index";
import TagAutoCompleteComponent from "../components/TagAutocomplete.svelte";
import { ApiClient } from "../api";

class TagAutocomplete extends Behavior {
  constructor(element) {
    super(element);
    const wrapper = document.createElement("div");
    const apiBaseUrl = document.documentElement.dataset.apiBaseUrl || "";
    const apiClient = new ApiClient(apiBaseUrl);

    new TagAutoCompleteComponent({
      target: wrapper,
      props: {
        id: element.id,
        name: element.name,
        value: element.value,
        placeholder: element.getAttribute("placeholder") || "",
        apiClient: apiClient,
        variant: element.getAttribute("variant"),
      },
    });

    element.replaceWith(wrapper.firstElementChild);
  }
}

registerBehavior("ld-tag-autocomplete", TagAutocomplete);
