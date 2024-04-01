const behaviorRegistry = {};

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
    });
  });
}

export function swap(element, html) {
  const dom = new DOMParser().parseFromString(html, "text/html");
  const newElement = dom.body.firstChild;
  element.replaceWith(newElement);
  applyBehaviors(newElement);
}

export function swapContent(element, html) {
  element.innerHTML = html;
  applyBehaviors(element);
}
