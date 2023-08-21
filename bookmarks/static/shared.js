const behaviorRegistry = {};

function registerBehavior(name, behavior) {
  behaviorRegistry[name] = behavior;
  applyBehaviors(document, [name]);
}

function applyBehaviors(container, behaviorNames = null) {
  if (!behaviorNames) {
    behaviorNames = Object.keys(behaviorRegistry);
  }

  behaviorNames.forEach((behaviorName) => {
    const behavior = behaviorRegistry[behaviorName];
    const elements = container.querySelectorAll(`[${behaviorName}]`);

    elements.forEach((element) => {
      element.__behaviors = element.__behaviors || [];
      const hasBehavior = element.__behaviors.some(
        (b) => b instanceof behavior,
      );

      if (hasBehavior) {
        return;
      }

      const behaviorInstance = new behavior(element);
      element.__behaviors.push(behaviorInstance);
    });
  });
}

function swap(element, html) {
  element.innerHTML = html;
  applyBehaviors(element);
}

linkding = linkding || {};
linkding.registerBehavior = registerBehavior;
linkding.applyBehaviors = applyBehaviors;
linkding.swap = swap;

class ConfirmButtonBehavior {
  constructor(element) {
    const button = element;
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

registerBehavior("ld-confirm-button", ConfirmButtonBehavior);

class TagAutocomplete {
  constructor(element) {
    const wrapper = document.createElement("div");
    const apiBaseUrl = document.documentElement.dataset.apiBaseUrl || "";
    const apiClient = new linkding.ApiClient(apiBaseUrl);

    new linkding.TagAutoComplete({
      target: wrapper,
      props: {
        id: element.id,
        name: element.name,
        value: element.value,
        apiClient: apiClient,
        variant: element.getAttribute("variant"),
      },
    });

    element.replaceWith(wrapper);
  }
}

registerBehavior("ld-tag-autocomplete", TagAutocomplete);
