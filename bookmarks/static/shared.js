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


    initConfirmationButtons()
})()