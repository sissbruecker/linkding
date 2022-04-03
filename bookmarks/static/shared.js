(function () {

    function initConfirmationButtons() {
        const buttonEls = document.querySelectorAll('.btn-confirmation');

        function showConfirmation(buttonEl) {
            const cancelEl = document.createElement(buttonEl.nodeName);
            cancelEl.innerText = 'Cancel';
            cancelEl.className = 'btn btn-link btn-sm btn-confirmation-action mr-1';
            cancelEl.addEventListener('click', function () {
                container.remove();
                buttonEl.style = '';
            });

            const confirmEl = document.createElement(buttonEl.nodeName);
            confirmEl.innerText = 'Confirm';
            confirmEl.className = 'btn btn-link btn-delete btn-sm btn-confirmation-action';

            if (buttonEl.nodeName === 'BUTTON') {
                confirmEl.type = buttonEl.type;
                confirmEl.name = buttonEl.name;
                confirmEl.value = buttonEl.value;
            }
            if (buttonEl.nodeName === 'A') {
                confirmEl.href = buttonEl.href;
            }

            const container = document.createElement('span');
            container.className = 'confirmation'
            container.appendChild(cancelEl);
            container.appendChild(confirmEl);
            buttonEl.parentElement.insertBefore(container, buttonEl);
            buttonEl.style = 'display: none';
        }

        buttonEls.forEach(function (linkEl) {
            linkEl.addEventListener('click', function (e) {
                e.preventDefault();
                showConfirmation(linkEl);
            });
        });
    }

    function initGlobalShortcuts() {
        // Focus search button
        document.addEventListener('keydown', function (event) {
            // Filter for shortcut key
            if (event.key !== 's') return;
            // Skip if event occurred within an input element
            const targetNodeName = event.target.nodeName;
            const isInputTarget = targetNodeName === 'INPUT'
                || targetNodeName === 'SELECT'
                || targetNodeName === 'TEXTAREA';

            if (isInputTarget) return;

            const searchInput = document.querySelector('input[type="search"]');

            if (searchInput) {
                searchInput.focus();
                event.preventDefault();
            }
        });

        // Add new bookmark
        document.addEventListener('keydown', function(event) {
            // Filter for new entry shortcut key
            if(event.key !== 'n') return;
            // Skip if event occurred within an input element
            const targetNodeName = event.target.nodeName;
            const isInputTarget = targetNodeName === 'INPUT'
                || targetNodeName === 'SELECT'
                || targetNodeName === 'TEXTAREA';

            if (isInputTarget) return;

            window.location.replace("/bookmarks/new");
        });
    }

    initConfirmationButtons();
    initGlobalShortcuts();
})()