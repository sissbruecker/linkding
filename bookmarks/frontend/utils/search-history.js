const SEARCH_HISTORY_KEY = "searchHistory";
const MAX_ENTRIES = 30;

export class SearchHistory {
  getHistory() {
    const historyJson = localStorage.getItem(SEARCH_HISTORY_KEY);
    return historyJson
      ? JSON.parse(historyJson)
      : {
          recent: [],
        };
  }

  pushCurrent() {
    // Skip if browser is not compatible
    if (!window.URLSearchParams) return;
    const urlParams = new URLSearchParams(window.location.search);
    const searchParam = urlParams.get("q");

    if (!searchParam) return;

    this.push(searchParam);
  }

  push(search) {
    const history = this.getHistory();

    history.recent.unshift(search);

    // Remove duplicates and clamp to max entries
    history.recent = history.recent.reduce((acc, cur) => {
      if (acc.length >= MAX_ENTRIES) return acc;
      if (acc.indexOf(cur) >= 0) return acc;
      acc.push(cur);
      return acc;
    }, []);

    const newHistoryJson = JSON.stringify(history);
    localStorage.setItem(SEARCH_HISTORY_KEY, newHistoryJson);
  }

  getRecentSearches(query, max) {
    const history = this.getHistory();

    return history.recent
      .filter(
        (search) =>
          !query || search.toLowerCase().indexOf(query.toLowerCase()) >= 0,
      )
      .slice(0, max);
  }
}
