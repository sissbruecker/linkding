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

// Update behaviors on Turbo events
// - turbo:load: initial page load, only listen once, afterward can rely on turbo:render
// - turbo:render: after page navigation, including back/forward, and failed form submissions
// - turbo:before-cache: before page navigation, reset DOM before caching
document.addEventListener(
  "turbo:load",
  () => {
    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
    });

    applyBehaviors(document.body);
  },
  { once: true },
);

document.addEventListener("turbo:render", () => {
  mutationObserver.observe(document.body, {
    childList: true,
    subtree: true,
  });

  applyBehaviors(document.body);
});

document.addEventListener("turbo:before-cache", () => {
  destroyBehaviors(document.body);
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
