(function () {
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

    // Init tag auto-complete
    function initTagAutoComplete() {
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

    initTagAutoComplete();
})()
