import { LitElement, html } from "lit";
import { cache } from "../cache.js";
import { getCurrentWord, getCurrentWordBounds } from "../util.js";

export class TagAutocomplete extends LitElement {
  static properties = {
    id: { type: String },
    name: { type: String },
    value: { type: String },
    placeholder: { type: String },
    ariaDescribedBy: { type: String, attribute: "aria-described-by" },
    variant: { type: String },
    isFocus: { state: true },
    isOpen: { state: true },
    suggestions: { state: true },
    selectedIndex: { state: true },
  };

  constructor() {
    super();
    this.id = "";
    this.name = "";
    this.value = "";
    this.placeholder = "";
    this.ariaDescribedBy = "";
    this.variant = "default";
    this.isFocus = false;
    this.isOpen = false;
    this.suggestions = [];
    this.selectedIndex = 0;
    this.input = null;
    this.suggestionList = null;
  }

  createRenderRoot() {
    return this;
  }

  firstUpdated() {
    this.input = this.querySelector("input");
    this.suggestionList = this.querySelector(".menu");
  }

  handleFocus() {
    this.isFocus = true;
  }

  handleBlur() {
    this.isFocus = false;
    this.close();
  }

  async handleInput(e) {
    this.input = e.target;

    const tags = await cache.getTags();
    const word = getCurrentWord(this.input);

    this.suggestions = word
      ? tags.filter(
          (tag) => tag.name.toLowerCase().indexOf(word.toLowerCase()) === 0,
        )
      : [];

    if (word && this.suggestions.length > 0) {
      this.open();
    } else {
      this.close();
    }
  }

  handleKeyDown(e) {
    if (this.isOpen && (e.keyCode === 13 || e.keyCode === 9)) {
      const suggestion = this.suggestions[this.selectedIndex];
      this.complete(suggestion);
      e.preventDefault();
    }
    if (e.keyCode === 27) {
      this.close();
      e.preventDefault();
    }
    if (e.keyCode === 38) {
      this.updateSelection(-1);
      e.preventDefault();
    }
    if (e.keyCode === 40) {
      this.updateSelection(1);
      e.preventDefault();
    }
  }

  open() {
    this.isOpen = true;
    this.selectedIndex = 0;
  }

  close() {
    this.isOpen = false;
    this.suggestions = [];
    this.selectedIndex = 0;
  }

  complete(suggestion) {
    const bounds = getCurrentWordBounds(this.input);
    const value = this.input.value;
    this.input.value =
      value.substring(0, bounds.start) +
      suggestion.name +
      " " +
      value.substring(bounds.end);
    this.input.dispatchEvent(new CustomEvent("change", { bubbles: true }));

    this.close();
  }

  updateSelection(dir) {
    const length = this.suggestions.length;
    let newIndex = this.selectedIndex + dir;

    if (newIndex < 0) newIndex = Math.max(length - 1, 0);
    if (newIndex >= length) newIndex = 0;

    this.selectedIndex = newIndex;

    // Scroll to selected list item
    setTimeout(() => {
      if (this.suggestionList) {
        const selectedListItem =
          this.suggestionList.querySelector("li.selected");
        if (selectedListItem) {
          selectedListItem.scrollIntoView({ block: "center" });
        }
      }
    }, 0);
  }

  render() {
    return html`
      <div class="form-autocomplete ${this.variant === "small" ? "small" : ""}">
        <!-- autocomplete input container -->
        <div
          class="form-autocomplete-input form-input ${this.isFocus
            ? "is-focused"
            : ""}"
        >
          <!-- autocomplete real input box -->
          <input
            id="${this.id}"
            name="${this.name}"
            .value="${this.value || ""}"
            placeholder="${this.placeholder || " "}"
            class="form-input"
            type="text"
            autocomplete="off"
            autocapitalize="off"
            aria-describedby="${this.ariaDescribedBy}"
            @input=${this.handleInput}
            @keydown=${this.handleKeyDown}
            @focus=${this.handleFocus}
            @blur=${this.handleBlur}
          />
        </div>

        <!-- autocomplete suggestion list -->
        <ul
          class="menu ${this.isOpen && this.suggestions.length > 0
            ? "open"
            : ""}"
        >
          <!-- menu list items -->
          ${this.suggestions.map(
            (tag, i) => html`
              <li
                class="menu-item ${this.selectedIndex === i ? "selected" : ""}"
              >
                <a
                  href="#"
                  @mousedown=${(e) => {
                    e.preventDefault();
                    this.complete(tag);
                  }}
                >
                  ${tag.name}
                </a>
              </li>
            `,
          )}
        </ul>
      </div>
    `;
  }
}

customElements.define("ld-tag-autocomplete", TagAutocomplete);
