import TagAutoComplete from "./components/TagAutocomplete.svelte";
import SearchAutoComplete from "./components/SearchAutoComplete.svelte";
import { ApiClient } from "./api";
import "./behaviors/bookmark-page";
import "./behaviors/bulk-edit";
import "./behaviors/confirm-button";
import "./behaviors/dropdown";
import "./behaviors/modal";
import "./behaviors/global-shortcuts";
import "./behaviors/tag-autocomplete";

export default {
  ApiClient,
  TagAutoComplete,
  SearchAutoComplete,
};
