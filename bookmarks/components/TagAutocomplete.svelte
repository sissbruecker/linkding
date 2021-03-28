<script>
    import {getCurrentWord, getCurrentWordBounds} from "./util";

    export let id;
    export let name;
    export let value;
    export let apiClient;
    export let variant = 'default';

    let tags = [];
    let isFocus = false;
    let isOpen = false;
    let input = null;

    let suggestions = [];
    let selectedIndex = 0;

    init();

    async function init() {
        // For now we cache all tags on load as the template did before
        try {
            tags = await apiClient.getTags({limit: 1000, offset: 0});
            tags.sort((left, right) => left.name.toLowerCase().localeCompare(right.name.toLowerCase()))
        } catch (e) {
            console.warn('TagAutocomplete: Error loading tag list');
        }
    }

    function handleFocus() {
        isFocus = true;
    }

    function handleBlur() {
        isFocus = false;
        close();
    }

    function handleInput(e) {
        input = e.target;

        const word = getCurrentWord(input);

        suggestions = word
            ? tags.filter(tag => tag.name.toLowerCase().indexOf(word.toLowerCase()) === 0)
            : [];

        if (word && suggestions.length > 0) {
            open();
        } else {
            close();
        }
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

    function open() {
        isOpen = true;
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
        input.value = value.substring(0, bounds.start) + suggestion.name + value.substring(bounds.end);

        close();
    }

    function updateSelection(dir) {

        const length = suggestions.length;
        let newIndex = selectedIndex + dir;

        if (newIndex < 0) newIndex = Math.max(length - 1, 0);
        if (newIndex >= length) newIndex = 0;

        selectedIndex = newIndex;
    }
</script>

<div class="form-autocomplete" class:small={variant === 'small'}>
    <!-- autocomplete input container -->
    <div class="form-autocomplete-input form-input" class:is-focused={isFocus}>
        <!-- autocomplete real input box -->
        <input id="{id}" name="{name}" value="{value ||''}" placeholder="&nbsp;"
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
                            {tag.name}
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

    .form-autocomplete.small .form-autocomplete-input {
        height: 1.4rem;
        min-height: 1.4rem;
    }
    .form-autocomplete.small .form-autocomplete-input input {
        margin: 0;
        padding: 0;
        font-size: 0.7rem;
    }
    .form-autocomplete.small .menu .menu-item {
        font-size: 0.7rem;
    }
</style>
