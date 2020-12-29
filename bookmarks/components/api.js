export class ApiClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl
    }

    getBookmarks(query, options = {limit: 100, offset: 0}) {
        const encodedQuery = encodeURIComponent(query)
        const url = `${this.baseUrl}bookmarks?q=${encodedQuery}&limit=${options.limit}&offset=${options.offset}`

        return fetch(url)
            .then(response => response.json())
            .then(data => data.results)
    }
}