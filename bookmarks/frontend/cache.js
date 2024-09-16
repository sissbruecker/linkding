import { api } from "./api.js";

class Cache {
  constructor(api) {
    this.api = api;

    // Reset cached tags after a form submission
    document.addEventListener("turbo:submit-end", () => {
      this.tagsPromise = null;
    });
  }

  getTags() {
    if (!this.tagsPromise) {
      this.tagsPromise = this.api
        .getTags({
          limit: 5000,
          offset: 0,
        })
        .then((tags) =>
          tags.sort((left, right) =>
            left.name.toLowerCase().localeCompare(right.name.toLowerCase()),
          ),
        )
        .catch((e) => {
          console.warn("Cache: Error loading tags", e);
          return [];
        });
    }

    return this.tagsPromise;
  }
}

export const cache = new Cache(api);
