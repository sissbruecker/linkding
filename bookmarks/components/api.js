export class ApiClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl
    }

    getBookmarks(query, options = {limit: 100, offset: 0}) {
        const url = `${this.baseUrl}bookmarks?q=${query}&limit=${options.limit}&offset=${options.offset}`

        return fetch(url)
            .then(response => response.json())
            .then(data => data.results)
    }
}