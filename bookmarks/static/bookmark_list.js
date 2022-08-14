(function () {
  function setupBulkEdit() {
    const bulkEditToggle = document.getElementById('bulk-edit-mode')
    const bulkEditBar = document.querySelector('.bulk-edit-bar')
    const singleToggles = document.querySelectorAll('.bulk-edit-toggle input')
    const allToggle = document.querySelector('.bulk-edit-all-toggle input')

    function isAllSelected() {
      let result = true

      singleToggles.forEach(function (toggle) {
        result = result && toggle.checked
      })

      return result
    }

    function selectAll() {
      singleToggles.forEach(function (toggle) {
        toggle.checked = true
      })
    }

    function deselectAll() {
      singleToggles.forEach(function (toggle) {
        toggle.checked = false
      })
    }

    // Toggle all
    allToggle.addEventListener('change', function (e) {
      if (e.target.checked) {
        selectAll()
      } else {
        deselectAll()
      }
    })

    // Toggle single
    singleToggles.forEach(function (toggle) {
      toggle.addEventListener('change', function () {
        allToggle.checked = isAllSelected()
      })
    })

    // Allow overflow when bulk edit mode is active to be able to display tag auto complete menu
    let bulkEditToggleTimeout
    if (bulkEditToggle.checked) {
      bulkEditBar.style.overflow = 'visible';
    }
    bulkEditToggle.addEventListener('change', function (e) {
      if (bulkEditToggleTimeout) {
        clearTimeout(bulkEditToggleTimeout);
        bulkEditToggleTimeout = null;
      }
      if (e.target.checked) {
        bulkEditToggleTimeout = setTimeout(function () {
          bulkEditBar.style.overflow = 'visible';
        }, 500);
      } else {
        bulkEditBar.style.overflow = 'hidden';
      }
    });
  }

  function setupBulkEditTagAutoComplete() {
    const wrapper = document.createElement('div');
    const tagInput = document.getElementById('bulk-edit-tags-input');
    const apiBaseUrl = document.documentElement.dataset.apiBaseUrl || '';
    const apiClient = new linkding.ApiClient(apiBaseUrl)

    new linkding.TagAutoComplete({
      target: wrapper,
      props: {
        id: 'bulk-edit-tags-input',
        name: tagInput.name,
        value: tagInput.value,
        apiClient: apiClient,
        variant: 'small'
      }
    });

    tagInput.parentElement.replaceChild(wrapper, tagInput);
  }

  function setupListNavigation() {
    // Add logic for navigating bookmarks with arrow keys
    document.addEventListener('keydown', event => {
      // Skip if event occurred within an input element
      // or does not use arrow keys
      const targetNodeName = event.target.nodeName;
      const isInputTarget = targetNodeName === 'INPUT'
        || targetNodeName === 'SELECT'
        || targetNodeName === 'TEXTAREA';
      const isArrowUp = event.key === 'ArrowUp';
      const isArrowDown = event.key === 'ArrowDown';

      if (isInputTarget || !(isArrowUp || isArrowDown)) {
        return;
      }
      event.preventDefault();

      // Detect current bookmark list item
      const path = event.composedPath();
      const currentItem = path.find(item => item.hasAttribute && item.hasAttribute('data-is-bookmark-item'));

      // Find next item
      let nextItem;
      if (currentItem) {
        nextItem = isArrowUp
          ? currentItem.previousElementSibling
          : currentItem.nextElementSibling;
      } else {
        // Select first item
        nextItem = document.querySelector('li[data-is-bookmark-item]');
      }
      // Focus first link
      if (nextItem) {
        nextItem.querySelector('a').focus();
      }
    });
  }

  setupBulkEdit();
  setupBulkEditTagAutoComplete();
  setupListNavigation();
})()
