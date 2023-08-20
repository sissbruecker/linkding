class ConfirmButton extends HTMLElement {
  connectedCallback() {
    const button = this.querySelector("button");
    button.dataset.type = button.type;
    button.dataset.name = button.name;
    button.dataset.value = button.value;
    button.removeAttribute("type");
    button.removeAttribute("name");
    button.removeAttribute("value");
    button.addEventListener("click", this.onClick.bind(this));
    this.button = button;
  }

  onClick(event) {
    event.preventDefault();

    const cancelButton = document.createElement(this.button.nodeName);
    cancelButton.type = "button";
    cancelButton.innerText = "Cancel";
    cancelButton.className = "btn btn-link btn-sm mr-1";
    cancelButton.addEventListener("click", this.reset.bind(this));

    const confirmButton = document.createElement(this.button.nodeName);
    confirmButton.type = this.button.dataset.type;
    confirmButton.name = this.button.dataset.name;
    confirmButton.value = this.button.dataset.value;
    confirmButton.innerText = "Confirm";
    confirmButton.className = "btn btn-link btn-sm";
    confirmButton.addEventListener("click", this.reset.bind(this));

    const container = document.createElement("span");
    container.className = "confirmation";
    container.append(cancelButton, confirmButton);
    this.container = container;

    this.button.before(container);
    this.button.classList.add("d-none");
  }

  reset() {
    setTimeout(() => {
      this.container.remove();
      this.button.classList.remove("d-none");
    });
  }
}

customElements.define("ld-confirm-button", ConfirmButton);

(function () {
  function initGlobalShortcuts() {
    // Focus search button
    document.addEventListener("keydown", function (event) {
      // Filter for shortcut key
      if (event.key !== "s") return;
      // Skip if event occurred within an input element
      const targetNodeName = event.target.nodeName;
      const isInputTarget =
        targetNodeName === "INPUT" ||
        targetNodeName === "SELECT" ||
        targetNodeName === "TEXTAREA";

      if (isInputTarget) return;

      const searchInput = document.querySelector('input[type="search"]');

      if (searchInput) {
        searchInput.focus();
        event.preventDefault();
      }
    });

    // Add new bookmark
    document.addEventListener("keydown", function (event) {
      // Filter for new entry shortcut key
      if (event.key !== "n") return;
      // Skip if event occurred within an input element
      const targetNodeName = event.target.nodeName;
      const isInputTarget =
        targetNodeName === "INPUT" ||
        targetNodeName === "SELECT" ||
        targetNodeName === "TEXTAREA";

      if (isInputTarget) return;

      window.location.assign("/bookmarks/new");
    });
  }

  initGlobalShortcuts();
})();
