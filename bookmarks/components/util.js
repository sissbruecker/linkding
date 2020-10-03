export function debounce(callback, delay = 250) {
    let timeoutId
    return (...args) => {
        clearTimeout(timeoutId)
        timeoutId = setTimeout(() => {
            timeoutId = null
            callback(...args)
        }, delay)
    }
}

export function clampText(text, maxChars = 30) {
    if(!text || text.length <= 30) return text

    return text.substr(0, maxChars) + '...'
}