<script>
    export let id;
    export let name;
    export let value;
    export let tags;

    let isFocus = false;
    let isOpen = false;
    let input = null;

    let suggestions = [];
    let selectedIndex = 0;

    function handleFocus() {
        isFocus = true;
    }

    function handleBlur() {
        isFocus = false;
        close();
    }

    function handleInput(e) {
        input = e.target;
        const word = getCurrentWord(e.target);

        if (!word) {
            close();
            return;
        }

        open(word);
    }

    function handleKeyDown(e) {
        if (isOpen && (e.keyCode === 13 || e.keyCode === 9)) {
            const suggestion = suggestions[selectedIndex];
            complete(suggestion);
            e.preventDefault();
        }
        if (e.keyCode === 27) {
            close();
            e.preventDefault();
        }
        if (e.keyCode === 38) {
            updateSelection(-1);
            e.preventDefault();
        }
        if (e.keyCode === 40) {
            updateSelection(1);
            e.preventDefault();
        }
    }

    function open(word) {
        isOpen = true;
        updateSuggestions(word);
        selectedIndex = 0;
    }

    function close() {
        isOpen = false;
        suggestions = [];
        selectedIndex = 0;
    }

    function complete(suggestion) {
        const bounds = getCurrentWordBounds(input);
        const value = input.value;
        input.value = value.substring(0, bounds.start) + suggestion + value.substring(bounds.end);

        close();
    }

    function getCurrentWordBounds() {
        const text = input.value;
        const end = input.selectionStart;
        let start = end;

        let currentChar = text.charAt(start - 1);

        while (currentChar && currentChar !== ' ' && start > 0) {
            start--;
            currentChar = text.charAt(start - 1);
        }

        return {start, end};
    }

    function getCurrentWord() {
        const bounds = getCurrentWordBounds(input);

        return input.value.substring(bounds.start, bounds.end);
    }

    function updateSuggestions(word) {
        suggestions = tags.filter(tag => tag.indexOf(word) === 0);
    }

    function updateSelection(dir) {

        const length = suggestions.length;
        let newIndex = selectedIndex + dir;

        if (newIndex < 0) newIndex = Math.max(length - 1, 0);
        if (newIndex >= length) newIndex = 0;

        selectedIndex = newIndex;
    }
</script>

<div class="form-autocomplete">
    <!-- autocomplete input container -->
    <div class="form-autocomplete-input form-input" class:is-focused={isFocus}>
        <!-- autocomplete real input box -->
        <input id="{id}" name="{name}" value="{value ||''}"
               class="form-input" type="text" autocomplete="off"
               on:input={handleInput} on:keydown={handleKeyDown}
               on:focus={handleFocus} on:blur={handleBlur}>
    </div>

    <!-- autocomplete suggestion list -->
    <ul class="menu" class:open={isOpen && suggestions.length > 0}>
        <!-- menu list items -->
        {#each suggestions as tag,i}
            <li class="menu-item" class:selected={selectedIndex === i}>
                <a href="#" on:mousedown|preventDefault={() => complete(tag)}>
                    <div class="tile tile-centered">
                        <div class="tile-content">
                            {tag}
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

    /* TODO: Should be read from theme */
    .menu-item.selected > a {
        background: #f1f1fc;
        color: #5755d9;
    }
</style>