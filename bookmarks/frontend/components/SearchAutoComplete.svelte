<script>
  import {SearchHistory} from "./SearchHistory";
  import {api} from "../api";
  import {cache} from "../cache";
  import {clampText, debounce, getCurrentWord, getCurrentWordBounds} from "../util";

  const searchHistory = new SearchHistory()

  export let name;
  export let placeholder;
  export let value;
  export let mode = '';
  export let search;
  export let linkTarget = '_blank';

  let isFocus = false;
  let isOpen = false;
  let suggestions = []
  let selectedIndex = undefined;
  let input = null;

  // Track current search query after loading the page
  searchHistory.pushCurrent()
  updateSuggestions()

  function handleFocus() {
    isFocus = true;
  }

  function handleBlur() {
    isFocus = false;
    close();
  }

  function handleInput(e) {
    value = e.target.value
    debouncedLoadSuggestions()
  }

  function handleKeyDown(e) {
    // Enter
    if (isOpen && selectedIndex !== undefined && (e.keyCode === 13 || e.keyCode === 9)) {
      const suggestion = suggestions.total[selectedIndex];
      if (suggestion) completeSuggestion(suggestion);
      e.preventDefault();
    }
    // Escape
    if (e.keyCode === 27) {
      close();
      e.preventDefault();
    }
    // Up arrow
    if (e.keyCode === 38) {
      updateSelection(-1);
      e.preventDefault();
    }
    // Down arrow
    if (e.keyCode === 40) {
      if (!isOpen) {
        loadSuggestions()
      } else {
        updateSelection(1);
      }
      e.preventDefault();
    }
  }

  function open() {
    isOpen = true;
  }

  function close() {
    isOpen = false;
    updateSuggestions()
    selectedIndex = undefined
  }

  function hasSuggestions() {
    return suggestions.total.length > 0
  }

  async function loadSuggestions() {

    let suggestionIndex = 0

    function nextIndex() {
      return suggestionIndex++
    }

    // Tag suggestions
    const tags = await cache.getTags();
    let tagSuggestions = []
    const currentWord = getCurrentWord(input)
    if (currentWord && currentWord.length > 1 && currentWord[0] === '#') {
      const searchTag = currentWord.substring(1, currentWord.length)
      tagSuggestions = (tags || []).filter(tag => tag.name.toLowerCase().indexOf(searchTag.toLowerCase()) === 0)
        .slice(0, 5)
        .map(tag => ({
          type: 'tag',
          index: nextIndex(),
          label: `#${tag.name}`,
          tagName: tag.name
        }))
    }

    // Recent search suggestions
    const recentSearches = searchHistory.getRecentSearches(value, 5).map(value => ({
      type: 'search',
      index: nextIndex(),
      label: value,
      value
    }))

    // Bookmark suggestions
    let bookmarks = []

    if (value && value.length >= 3) {
      const path = mode ? `/${mode}` : ''
      const suggestionSearch = {
        ...search,
        q: value
      }
      const fetchedBookmarks = await api.listBookmarks(suggestionSearch, {limit: 5, offset: 0, path})
      bookmarks = fetchedBookmarks.map(bookmark => {
        const fullLabel = bookmark.title || bookmark.url
        const label = clampText(fullLabel, 60)
        return {
          type: 'bookmark',
          index: nextIndex(),
          label,
          bookmark
        }
      })
    }

    updateSuggestions(recentSearches, bookmarks, tagSuggestions)

    if (hasSuggestions()) {
      open()
    } else {
      close()
    }
  }

  const debouncedLoadSuggestions = debounce(loadSuggestions)

  function updateSuggestions(recentSearches, bookmarks, tagSuggestions) {
    recentSearches = recentSearches || []
    bookmarks = bookmarks || []
    tagSuggestions = tagSuggestions || []
    suggestions = {
      recentSearches,
      bookmarks,
      tags: tagSuggestions,
      total: [
        ...tagSuggestions,
        ...recentSearches,
        ...bookmarks,
      ]
    }
  }

  function completeSuggestion(suggestion) {
    if (suggestion.type === 'search') {
      value = suggestion.value
      close()
    }
    if (suggestion.type === 'bookmark') {
      window.open(suggestion.bookmark.url, linkTarget)
      close()
    }
    if (suggestion.type === 'tag') {
      const bounds = getCurrentWordBounds(input);
      const inputValue = input.value;
      input.value = inputValue.substring(0, bounds.start) + `#${suggestion.tagName} ` + inputValue.substring(bounds.end);
      close()
    }
  }

  function updateSelection(dir) {

    const length = suggestions.total.length;

    if (length === 0) return

    if (selectedIndex === undefined) {
      selectedIndex = dir > 0 ? 0 : Math.max(length - 1, 0)
      return
    }

    let newIndex = selectedIndex + dir;

    if (newIndex < 0) newIndex = Math.max(length - 1, 0);
    if (newIndex >= length) newIndex = 0;

    selectedIndex = newIndex;
  }
</script>

<div class="form-autocomplete">
  <div class="form-autocomplete-input form-input" class:is-focused={isFocus}>
    <input type="search" class="form-input" name="{name}" placeholder="{placeholder}" autocomplete="off" value="{value}"
           bind:this={input}
           on:input={handleInput} on:keydown={handleKeyDown} on:focus={handleFocus} on:blur={handleBlur}>
  </div>

  <ul class="menu" class:open={isOpen}>
    {#if suggestions.tags.length > 0}
      <li class="menu-item group-item">Tags</li>
    {/if}
    {#each suggestions.tags as suggestion}
      <li class="menu-item" class:selected={selectedIndex === suggestion.index}>
        <a href="#" on:mousedown|preventDefault={() => completeSuggestion(suggestion)}>
          {suggestion.label}
        </a>
      </li>
    {/each}

    {#if suggestions.recentSearches.length > 0}
      <li class="menu-item group-item">Recent Searches</li>
    {/if}
    {#each suggestions.recentSearches as suggestion}
      <li class="menu-item" class:selected={selectedIndex === suggestion.index}>
        <a href="#" on:mousedown|preventDefault={() => completeSuggestion(suggestion)}>
          {suggestion.label}
        </a>
      </li>
    {/each}

    {#if suggestions.bookmarks.length > 0}
      <li class="menu-item group-item">Bookmarks</li>
    {/if}
    {#each suggestions.bookmarks as suggestion}
      <li class="menu-item" class:selected={selectedIndex === suggestion.index}>
        <a href="#" on:mousedown|preventDefault={() => completeSuggestion(suggestion)}>
          {suggestion.label}
        </a>
      </li>
    {/each}
  </ul>
</div>

<style>
    .menu {
        display: none;
        max-height: 400px;
        overflow: auto;
    }

    .menu.open {
        display: block;
    }

    .form-autocomplete-input {
        padding: 0;
    }

    .form-autocomplete-input.is-focused {
        z-index: 2;
    }

</style>
