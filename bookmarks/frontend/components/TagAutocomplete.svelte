<script>
  import {cache} from "../cache";
  import {getCurrentWord, getCurrentWordBounds} from "../util";

  export let id;
  export let name;
  export let value;
  export let placeholder;
  export let variant = 'default';

  let isFocus = false;
  let isOpen = false;
  let input = null;
  let suggestionList = null;

  let suggestions = [];
  let selectedIndex = 0;

  function handleFocus() {
    isFocus = true;
  }

  function handleBlur() {
    isFocus = false;
    close();
  }

  async function handleInput(e) {
    input = e.target;

    const tags = await cache.getTags();
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
    input.value = value.substring(0, bounds.start) + suggestion.name + ' ' + value.substring(bounds.end);

    close();
  }

  function updateSelection(dir) {

    const length = suggestions.length;
    let newIndex = selectedIndex + dir;

    if (newIndex < 0) newIndex = Math.max(length - 1, 0);
    if (newIndex >= length) newIndex = 0;

    selectedIndex = newIndex;

    // Scroll to selected list item
    setTimeout(() => {
      if (suggestionList) {
        const selectedListItem = suggestionList.querySelector('li.selected');
        if (selectedListItem) {
          selectedListItem.scrollIntoView({block: 'center'});
        }
      }
    }, 0);
  }
</script>

<div class="form-autocomplete" class:small={variant === 'small'}>
  <!-- autocomplete input container -->
  <div class="form-autocomplete-input form-input" class:is-focused={isFocus}>
    <!-- autocomplete real input box -->
    <input id="{id}" name="{name}" value="{value ||''}" placeholder="{placeholder || ' '}"
           class="form-input" type="text" autocomplete="off" autocapitalize="off"
           on:input={handleInput} on:keydown={handleKeyDown}
           on:focus={handleFocus} on:blur={handleBlur}>
  </div>

  <!-- autocomplete suggestion list -->
  <ul class="menu" class:open={isOpen && suggestions.length > 0}
      bind:this={suggestionList}>
    <!-- menu list items -->
    {#each suggestions as tag,i}
      <li class="menu-item" class:selected={selectedIndex === i}>
        <a href="#" on:mousedown|preventDefault={() => complete(tag)}>
          {tag.name}
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
        box-sizing: border-box;
        height: var(--control-size);
        min-height: var(--control-size);
        padding: 0;
    }

    .form-autocomplete-input input {
        width: 100%;
        height: 100%;
        border: none;
        margin: 0;
    }

    .form-autocomplete.small .form-autocomplete-input {
        height: var(--control-size-sm);
        min-height: var(--control-size-sm);
    }

    .form-autocomplete.small .form-autocomplete-input input {
        padding: 0.05rem 0.3rem;
        font-size: var(--font-size-sm);
    }

    .form-autocomplete.small .menu .menu-item {
        font-size: var(--font-size-sm);
    }
</style>
