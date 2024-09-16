export class Api {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  listBookmarks(search, options = { limit: 100, offset: 0, path: "" }) {
    const query = [`limit=${options.limit}`, `offset=${options.offset}`];
    Object.keys(search).forEach((key) => {
      const value = search[key];
      if (value) {
        query.push(`${key}=${encodeURIComponent(value)}`);
      }
    });
    const queryString = query.join("&");
    const url = `${this.baseUrl}bookmarks${options.path}/?${queryString}`;

    return fetch(url)
      .then((response) => response.json())
      .then((data) => data.results);
  }

  getTags(options = { limit: 100, offset: 0 }) {
    const url = `${this.baseUrl}tags/?limit=${options.limit}&offset=${options.offset}`;

    return fetch(url)
      .then((response) => response.json())
      .then((data) => data.results);
  }
}

const apiBaseUrl = document.documentElement.dataset.apiBaseUrl || "";
export const api = new Api(apiBaseUrl);
