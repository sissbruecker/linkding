import { api } from "./api";

class Tags {
  api;
  staticTable;

  constructor(api) {
    this.api = api;

    // Reset cached tags after a form submission
    document.addEventListener("turbo:submit-end", () => {
      this.staticTable = null;
    });
  }

  async getTags(
    fetchType /* : 'static' | 'dynamic' */,
    matchType /*: 'starts_with' | 'contains'*/,
    word /*: string */,
  ) {
    if (fetchType !== "static" && fetchType !== "dynamic") {
      if (fetchType !== undefined) {
        console.warn(`Invalid fetch type passed as fetch type:`, fetchType);
      }

      fetchType = "static";
    }

    if (matchType !== "starts_with" && matchType !== "contains") {
      if (matchType !== undefined) {
        console.warn(`Invalid match type passed as match type:`, matchType);
      }

      matchType = "starts_with";
    }

    switch (fetchType) {
      case "static":
        return this._getTypesWithStaticTable(matchType, word);

      case "dynamic":
        return this._getTypesWithDynamicTable(matchType, word);

      default:
        console.error(`unreachable`);
    }
  }

  async _getTypesWithStaticTable(
    matchType /*: 'starts_with' | 'contains'*/,
    word /*: string */,
  ) {
    if (!this.staticTable) {
      this.staticTable = await this._getAllTags();
    }

    return this._matchTags(this.staticTable, matchType, word);
  }

  async _getTypesWithDynamicTable(
    matchType /*: 'starts_with' | 'contains'*/,
    word /*: string */,
  ) {
    const table = await this._getSpecificTags(word);

    return this._matchTags(table, matchType, word);
  }

  async _getAllTags() {
    return this.api
      .getTags({
        offset: 0,
        limit: 5000,
      })
      .catch((e) => {
        console.error(`Tags: Error fetching tags:`, e);
        return [];
      });
  }

  async _getSpecificTags(word /*: string */) {
    if (word) {
      return this.api
        .getTags({
          offset: 0,
          limit: 50,
          word: word,
        })
        .catch((e) => {
          console.error(`Tags: Error fetching specific ${word} tags:`, e);
          return [];
        });
    } else {
      return this.api
        .getTags({
          offset: 0,
          limit: 50,
        })
        .catch((e) => {
          console.error(`Tags: Error fetching specific ${word} tags:`, e);
          return [];
        });
    }
  }

  _matchTags(
    tags,
    matchType /*: 'starts_with' | 'contains'*/,
    word /*: string */,
  ) {
    if (!Array.isArray(tags)) return [];

    word = word.toLocaleLowerCase();

    return tags.filter((tag) => {
      const lower = tag.name.toLocaleLowerCase();
      return matchType === "starts_with"
        ? lower.startsWith(word)
        : lower.includes(word);
    });
  }
}

export const tags = new Tags(api);
