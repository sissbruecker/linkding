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

export function swap(element, html, target = null) {
  const dom = new DOMParser().parseFromString(html, "text/html");
  const contents = Array.from(dom.body.children);

  let targetElement = element;
  let strategy = "innerHTML";
  if (target) {
    const parts = target.split("|");
    targetElement = document.querySelector(parts[0]);
    strategy = parts[1] || "innerHTML";
  }

  switch (strategy) {
    case "append":
      targetElement.append(...contents);
      break;
    default:
      targetElement.innerHTML = "";
      targetElement.append(...contents);
  }
  applyBehaviors(targetElement);
}

export function swapContent(element, html) {
  element.innerHTML = html;
  applyBehaviors(element);
}

export function fireEvents(events) {
  events.split(",").forEach((eventName) => {
    const targets = Array.from(
      document.querySelectorAll(`[ld-on='${eventName}']`),
    );
    targets.forEach((target) => {
      target.dispatchEvent(new CustomEvent(eventName));
    });
  });
}
