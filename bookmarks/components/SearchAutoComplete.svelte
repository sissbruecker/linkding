<script>
    import {SearchHistory} from "./SearchHistory";

    const searchHistory = new SearchHistory()

    export let name;
    export let placeholder;
    export let value;

    let isFocus = false;
    let isOpen = false;
    let suggestions = []
    let selectedIndex = undefined;

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
        loadSuggestions()
    }

    function handleKeyDown(e) {
        // Enter
        if (isOpen && (e.keyCode === 13 || e.keyCode === 9)) {
            const suggestion = suggestions.total[selectedIndex];
            completeSuggestion(suggestion);
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

    function loadSuggestions() {

        let suggestionIndex = 0

        function nextIndex() {
            return suggestionIndex++
        }

        const search = searchHistory.getRecentSearches(value, 5).map(value => ({
            type: 'search',
            index: nextIndex(),
            value
        }))

        updateSuggestions(search)

        if (hasSuggestions()) {
            open()
        } else {
            close()
        }
    }

    function updateSuggestions(search) {
        search = search || []
        suggestions = {
            search,
            total: [
                ...search
            ]
        }

        console.log(suggestions)
    }

    function completeSuggestion(suggestion) {
        if(suggestion.type === 'search') {
            value = suggestion.value
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
    <div class="form-autocomplete-input" class:is-focused={isFocus}>
        <input type="search" name="{name}" placeholder="{placeholder}" autocomplete="off" value="{value}"
               on:input={handleInput} on:keydown={handleKeyDown} on:focus={handleFocus} on:blur={handleBlur}>
    </div>

    <ul class="menu" class:open={isOpen}>
        {#if suggestions.search.length > 0}
            <li class="menu-item group-item">Recent Searches</li>
        {/if}
        {#each suggestions.search as suggestion}
            <li class="menu-item" class:selected={selectedIndex === suggestion.index}>
                <a href="#"  on:mousedown|preventDefault={() => completeSuggestion(suggestion)}>
                    <div class="tile tile-centered">
                        <div class="tile-content">
                            {suggestion.value}
                        </div>
                    </div>
                </a>
            </li>
        {/each}
    </ul>
</div>

<style>
    .menu {
        display: none;
        max-height: 200px;
        overflow: auto;
    }

    .menu.open {
        display: block;
    }

    .form-autocomplete-input {
        padding: 0;
    }

    /* TODO: Should be read from theme */
    .menu-item.selected > a {
        background: #f1f1fc;
        color: #5755d9;
    }

    .group-item, .group-item:hover {
        color: #999999;
        text-transform: uppercase;
        background: none;
        font-size: 0.6rem;
        font-weight: bold;
    }
</style>