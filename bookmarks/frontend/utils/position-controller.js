import {
  arrow,
  autoUpdate,
  computePosition,
  flip,
  offset,
  shift,
} from "@floating-ui/dom";

export class PositionController {
  constructor(options) {
    this.anchor = options.anchor;
    this.overlay = options.overlay;
    this.arrow = options.arrow;
    this.placement = options.placement || "bottom";
    this.offset = options.offset;
    this.autoWidth = options.autoWidth || false;
    this.autoUpdateCleanup = null;
  }

  enable() {
    if (!this.autoUpdateCleanup) {
      this.autoUpdateCleanup = autoUpdate(this.anchor, this.overlay, () =>
        this.updatePosition(),
      );
    }
  }

  disable() {
    if (this.autoUpdateCleanup) {
      this.autoUpdateCleanup();
      this.autoUpdateCleanup = null;
    }
  }

  updatePosition() {
    const middleware = [flip(), shift()];
    if (this.arrow) {
      middleware.push(arrow({ element: this.arrow }));
    }
    if (this.offset) {
      middleware.push(offset(this.offset));
    }
    computePosition(this.anchor, this.overlay, {
      placement: this.placement,
      strategy: "fixed",
      middleware,
    }).then(({ x, y, placement, middlewareData }) => {
      Object.assign(this.overlay.style, {
        left: `${x}px`,
        top: `${y}px`,
      });

      this.overlay.classList.remove("top-aligned", "bottom-aligned");
      this.overlay.classList.add(`${placement}-aligned`);

      if (this.arrow) {
        const { x, y } = middlewareData.arrow;
        Object.assign(this.arrow.style, {
          left: x != null ? `${x}px` : "",
          top: y != null ? `${y}px` : "",
        });
      }
    });

    if (this.autoWidth) {
      const width = this.anchor.offsetWidth;
      this.overlay.style.width = `${width}px`;
    }
  }
}
