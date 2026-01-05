import { html, nothing } from "lit";
import { TurboLitElement } from "../utils/element.js";
import { getCurrentWord, getCurrentWordBounds } from "../utils/input.js";
import { PositionController } from "../utils/position-controller.js";
import { cache } from "../utils/tag-cache.js";

export class TagAutocomplete extends TurboLitElement {
  static properties = {
    inputId: { type: String, attribute: "input-id" },
    inputName: { type: String, attribute: "input-name" },
    inputValue: { type: String, attribute: "input-value" },
    inputClass: { type: String, attribute: "input-class" },
    inputPlaceholder: { type: String, attribute: "input-placeholder" },
    inputAriaDescribedBy: { type: String, attribute: "input-aria-describedby" },
    variant: { type: String },
    isFocus: { state: true },
    isOpen: { state: true },
    suggestions: { state: true },
    selectedIndex: { state: true },
  };

  constructor() {
    super();
    this.inputId = "";
    this.inputName = "";
    this.inputValue = "";
    this.inputPlaceholder = "";
    this.inputAriaDescribedBy = "";
    this.variant = "default";
    this.isFocus = false;
    this.isOpen = false;
    this.suggestions = [];
    this.selectedIndex = 0;
    this.input = null;
    this.suggestionList = null;
  }

  firstUpdated() {
    this.input = this.querySelector("input");
    this.suggestionList = this.querySelector(".menu");
    this.positionController = new PositionController({
      anchor: this.input,
      overlay: this.suggestionList,
      autoWidth: true,
      placement: "bottom-start",
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.close();
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
    this.positionController.enable();
  }

  close() {
    this.isOpen = false;
    this.suggestions = [];
    this.selectedIndex = 0;
    this.positionController.disable();
  }

  complete(suggestion) {
    const bounds = getCurrentWordBounds(this.input);
    const value = this.input.value;
    this.input.value =
      value.substring(0, bounds.start) +
      suggestion.name +
      " " +
      value.substring(bounds.end);
    this.dispatchEvent(new CustomEvent("input", { bubbles: true }));

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
            id="${this.inputId || nothing}"
            name="${this.inputName || nothing}"
            .value="${this.inputValue || ""}"
            placeholder="${this.inputPlaceholder || " "}"
            class="form-input ${this.inputClass || ""}"
            type="text"
            autocomplete="off"
            autocapitalize="off"
            aria-describedby="${this.inputAriaDescribedBy || nothing}"
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
