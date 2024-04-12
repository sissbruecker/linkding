const behaviorRegistry = {};
const debug = false;

const mutationObserver = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    mutation.removedNodes.forEach((node) => {
      if (node instanceof HTMLElement && !node.isConnected) {
        destroyBehaviors(node);
      }
    });
    mutation.addedNodes.forEach((node) => {
      if (node instanceof HTMLElement && node.isConnected) {
        applyBehaviors(node);
      }
    });
  });
});

mutationObserver.observe(document.body, {
  childList: true,
  subtree: true,
});

export class Behavior {
  constructor(element) {
    this.element = element;
  }

  destroy() {}
}

Behavior.interacting = false;

export function registerBehavior(name, behavior) {
  behaviorRegistry[name] = behavior;
  applyBehaviors(document, [name]);
}

export function applyBehaviors(container, behaviorNames = null) {
  if (!behaviorNames) {
    behaviorNames = Object.keys(behaviorRegistry);
  }

  behaviorNames.forEach((behaviorName) => {
    const behavior = behaviorRegistry[behaviorName];
    const elements = Array.from(
      container.querySelectorAll(`[${behaviorName}]`),
    );

    // Include the container element if it has the behavior
    if (container.hasAttribute && container.hasAttribute(behaviorName)) {
      elements.push(container);
    }

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
      if (debug) {
        console.log(
          `[Behavior] ${behaviorInstance.constructor.name} initialized`,
        );
      }
    });
  });
}

export function destroyBehaviors(element) {
  const behaviorNames = Object.keys(behaviorRegistry);

  behaviorNames.forEach((behaviorName) => {
    const elements = Array.from(element.querySelectorAll(`[${behaviorName}]`));
    elements.push(element);

    elements.forEach((element) => {
      if (!element.__behaviors) {
        return;
      }

      element.__behaviors.forEach((behavior) => {
        behavior.destroy();
        if (debug) {
          console.log(`[Behavior] ${behavior.constructor.name} destroyed`);
        }
      });
      delete element.__behaviors;
    });
  });
}

export function swap(element, html, options) {
  const dom = new DOMParser().parseFromString(html, "text/html");

  let targetElement = element;
  let strategy = "innerHTML";
  if (options.target) {
    const parts = options.target.split("|");
    targetElement =
      parts[0] === "self" ? element : document.querySelector(parts[0]);
    strategy = parts[1] || "innerHTML";
  }

  let contents = Array.from(dom.body.children);
  if (options.select) {
    contents = Array.from(dom.querySelectorAll(options.select));
  }

  switch (strategy) {
    case "append":
      targetElement.append(...contents);
      break;
    case "outerHTML":
      targetElement.parentElement.replaceChild(contents[0], targetElement);
      break;
    case "innerHTML":
    default:
      Array.from(targetElement.children).forEach((child) => {
        child.remove();
      });
      targetElement.append(...contents);
  }
}

export function fireEvents(events) {
  if (!events) {
    return;
  }
  events.split(",").forEach((eventName) => {
    const targets = Array.from(
      document.querySelectorAll(`[ld-on='${eventName}']`),
    );
    targets.push(document);
    targets.forEach((target) => {
      target.dispatchEvent(new CustomEvent(eventName));
    });
  });
}
