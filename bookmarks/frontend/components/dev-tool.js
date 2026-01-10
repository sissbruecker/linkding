import { LitElement, html, css } from "lit";

class DevTool extends LitElement {
  static properties = {
    profile: { type: Object, state: true },
    formAction: { type: String, attribute: "data-form-action" },
    csrfToken: { type: String, attribute: "data-csrf-token" },
    isOpen: { type: Boolean, state: true },
  };

  static styles = css`
    :host {
      position: fixed;
      bottom: 1rem;
      right: 1rem;
      z-index: 10000;
    }

    .button {
      background: var(--btn-primary-bg-color);
      color: var(--btn-primary-text-color);
      border: none;
      padding: var(--unit-2);
      border-radius: var(--border-radius);
      box-shadow: var(--btn-box-shadow);
      cursor: pointer;
      height: auto;
      line-height: 0;
    }

    .overlay {
      display: none;
      position: absolute;
      bottom: 100%;
      right: 0;
      background: var(--body-color);
      color: var(--text-color);
      border: 1px solid var(--border-color);
      border-radius: var(--border-radius);
      padding: var(--unit-2);
      margin-bottom: var(--unit-2);
      min-width: 220px;
      box-shadow: var(--box-shadow-lg);
      font-size: var(--font-size-sm);
    }

    :host([open]) .overlay {
      display: block;
    }

    h3 {
      margin: 0 0 var(--unit-2) 0;
    }

    label {
      display: flex;
      align-items: center;
      gap: var(--unit-1);
      cursor: pointer;
    }

    label:has(select) {
      margin-bottom: var(--unit-1);
    }

    label:has(select) span {
      min-width: 100px;
    }

    hr {
      margin: var(--unit-2) 0;
      border: none;
      border-top: 1px solid var(--border-color);
    }
  `;

  static fields = [
    {
      type: "select",
      key: "theme",
      label: "Theme",
      options: [
        { value: "auto", label: "Auto" },
        { value: "light", label: "Light" },
        { value: "dark", label: "Dark" },
      ],
    },
    {
      type: "select",
      key: "bookmark_date_display",
      label: "Date",
      options: [
        { value: "relative", label: "Relative" },
        { value: "absolute", label: "Absolute" },
        { value: "hidden", label: "Hidden" },
      ],
    },
    {
      type: "select",
      key: "bookmark_description_display",
      label: "Description",
      options: [
        { value: "inline", label: "Inline" },
        { value: "separate", label: "Separate" },
      ],
    },
    { type: "checkbox", key: "enable_favicons", label: "Favicons" },
    { type: "checkbox", key: "enable_preview_images", label: "Preview images" },
    { type: "checkbox", key: "display_url", label: "Display URL" },
    { type: "checkbox", key: "permanent_notes", label: "Permanent notes" },
    { type: "checkbox", key: "collapse_side_panel", label: "Collapse sidebar" },
    { type: "checkbox", key: "sticky_pagination", label: "Sticky pagination" },
    { type: "checkbox", key: "hide_bundles", label: "Hide bundles" },
  ];

  constructor() {
    super();
    this.isOpen = false;
    this.profile = {};
    this._onOutsideClick = this._onOutsideClick.bind(this);
  }

  connectedCallback() {
    super.connectedCallback();
    const profileData = document.getElementById("json_profile");
    this.profile = JSON.parse(profileData.textContent || "{}");
    document.addEventListener("click", this._onOutsideClick);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    document.removeEventListener("click", this._onOutsideClick);
  }

  _onOutsideClick(e) {
    if (!this.contains(e.target) && this.isOpen) {
      this.isOpen = false;
      this.removeAttribute("open");
    }
  }

  _toggle() {
    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      this.setAttribute("open", "");
    } else {
      this.removeAttribute("open");
    }
  }

  _handleChange(key, value) {
    this.profile = { ...this.profile, [key]: value };
    if (key === "theme") {
      const themeLinks = document.head.querySelectorAll('link[href*="theme"]');
      themeLinks.forEach((link) => link.remove());
    }
    this._submitForm();
  }

  _renderField(field) {
    switch (field.type) {
      case "checkbox":
        return html`
          <label>
            <input
              type="checkbox"
              .checked=${this.profile[field.key] || false}
              @change=${(e) => this._handleChange(field.key, e.target.checked)}
            />
            ${field.label}
          </label>
        `;
      case "select":
        return html`
          <label>
            <span>${field.label}:</span>
            <select
              @change=${(e) => this._handleChange(field.key, e.target.value)}
            >
              ${field.options.map(
                (opt) => html`
                  <option
                    value=${opt.value}
                    ?selected=${this.profile[field.key] === opt.value}
                  >
                    ${opt.label}
                  </option>
                `,
              )}
            </select>
          </label>
        `;
      case "divider":
        return html`<hr />`;
      default:
        return null;
    }
  }

  async _submitForm() {
    const formData = new FormData();
    formData.append("csrfmiddlewaretoken", this.csrfToken);

    // Profile fields
    for (const [key, value] of Object.entries(this.profile)) {
      if (typeof value === "boolean" && value) {
        formData.append(key, "on");
      } else if (typeof value !== "boolean") {
        formData.append(key, value);
      }
    }

    // Submit button name that settings.update expects
    formData.append("update_profile", "1");

    await fetch(this.formAction, {
      method: "POST",
      body: formData,
    });

    const url = new URL(window.location);
    url.searchParams.set("ts", Date.now().toString());
    window.history.replaceState({}, "", url);

    Turbo.visit(url.toString());
  }

  render() {
    return html`
      <button class="button" @click=${() => this._toggle()}>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path stroke="none" d="M0 0h24v24H0z" fill="none" />
          <path
            d="M10.325 4.317c.426 -1.756 2.924 -1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543 -.94 3.31 .826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756 .426 1.756 2.924 0 3.35a1.724 1.724 0 0 0 -1.066 2.573c.94 1.543 -.826 3.31 -2.37 2.37a1.724 1.724 0 0 0 -2.572 1.065c-.426 1.756 -2.924 1.756 -3.35 0a1.724 1.724 0 0 0 -2.573 -1.066c-1.543 .94 -3.31 -.826 -2.37 -2.37a1.724 1.724 0 0 0 -1.065 -2.572c-1.756 -.426 -1.756 -2.924 0 -3.35a1.724 1.724 0 0 0 1.066 -2.573c-.94 -1.543 .826 -3.31 2.37 -2.37c1 .608 2.296 .07 2.572 -1.065"
          />
          <path d="M9 12a3 3 0 1 0 6 0a3 3 0 0 0 -6 0" />
        </svg>
      </button>
      <div class="overlay">
        <h3>Dev Tools</h3>
        ${DevTool.fields.map((field) => this._renderField(field))}
      </div>
    `;
  }
}

customElements.define("ld-dev-tool", DevTool);
