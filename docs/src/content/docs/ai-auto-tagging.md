---
title: "AI auto-tagging"
description: "How to automatically assign tags to bookmarks using AI"
---

AI auto-tagging allows linkding to automatically assign tags to bookmarks using AI. Unlike [rule-based auto-tagging](/auto-tagging), which matches URL patterns, AI auto-tagging analyzes the bookmark's URL, title, and description to suggest relevant tags from your predefined allowed tags.

## How it works

When you create a bookmark without manually adding tags, linkding can use AI to analyze the bookmark content and suggest relevant tags. The AI will only suggest tags from your allowed tags, ensuring consistency with your existing tagging system.
Key features:
- **Automatic tagging**: Tags are suggested when creating new bookmarks without manual tags
- **Allowed tags**: AI only suggests tags from your predefined list
- **Smart analysis**: Uses bookmark URL, title, and description to determine relevance
- **Bulk operations**: Regenerate AI tags for existing bookmarks using the bulk "Refresh AI tags" action
- **Flexible providers**: Works with OpenAI or any OpenAI-compatible API

## Configuration

AI auto-tagging can be configured in your general settings. The following settings are required:

### API key

Your API key for the AI service. This field is required when using OpenAI or other cloud-based providers that require authentication.

**Not required** if you're using a self-hosted API that doesn't require authentication (such as a local Ollama instance).

### Model name

The name of the AI model to use for tag suggestions. **Important**: The model must support [structured outputs](https://platform.openai.com/docs/guides/structured-outputs).

Examples: `gpt-5-nano`, `gemma3:4b` (check your provider's documentation for supported models).

### Base URL

Optional, leave blank to use OpenAI's default API endpoint.

You can use any OpenAI-compatible API by providing a custom base URL. This includes:
- **Self-hosted**:
  - Ollama: `http://localhost:11434/v1`
- **Cloud-based**:
  - Perplexity: `https://api.perplexity.ai`
  - OpenRouter: `https://openrouter.ai/api/v1`
  - Any other OpenAI-compatible provider

When using a custom base URL, API key validation is skipped, allowing you to use services without authentication.

### Allowed tags

A newline-separated list of tags that the AI can suggest.

The AI will only suggest tags from this list. This ensures consistency with your existing tagging system.

Example:
```
programming
python
javascript
web-development
ai
tutorial
documentation
```

## Usage

### Automatic tagging

AI auto-tagging runs automatically when you create bookmarks **without manually adding tags**. The suggested tags will be added to the bookmark automatically.

If you manually add tags when creating a bookmark, AI auto-tagging will not run for that bookmark.

### Bulk refresh

To regenerate AI tags for existing bookmarks:

1. Select the bookmarks you want to update
2. Open the bulk edit menu
3. Click "Refresh AI tags"

This will replace the existing tags with new AI-generated suggestions based on your current allowed tags.

## Privacy and cost considerations

### Data sharing

When using AI auto-tagging, the following bookmark data is sent to the AI provider:
- URL
- Title
- Description
- Allowed tags

The actual content of the bookmarked web page is **not** sent to the AI provider.

### API costs

AI auto-tagging uses API calls to generate tag suggestions, which may incur costs depending on your provider.

Each bookmark without manual tags will trigger one API call. Bulk operations will create one API call per bookmark.

#### Estimated cost analysis

Using OpenAI's `gpt-5-nano` model at $0.05 per 1M input tokens and $0.4 per 1M output tokens:

**Average cost per bookmark: ~$0.000043**

- Input: ~250 tokens, cost: $0.0000125
- Output: ~100 tokens, cost: $0.00004

| Volume | Cost |
|--------|------|
| 100 bookmarks | ~$0.0043 |
| 1,000 bookmarks | ~$0.043 |

**Note**: Self-hosted solutions like Ollama are free to use. Pricing is approximate and may change.

## Troubleshooting

### Tags are not being suggested

Check that:
1. You have configured all required fields
2. Your API key is valid (if required by your provider)
3. The model you specified supports structured outputs
4. Your allowed tags list is not empty
5. You're creating bookmarks without manually adding tags

### API authentication errors

- **OpenAI**: Verify your API key is correct and has sufficient credits
- **Custom providers**: Ensure your base URL is correct and the service is accessible
- **Self-hosted**: Check that your service is running and reachable from the linkding instance

## Example configurations

### OpenAI

- **API key**: Your OpenAI API key (starts with `sk-`)
- **Model name**: `gpt-5-nano` (recommended for cost-effectiveness)
- **Base URL**: Leave blank
- **Allowed tags**: Your tag list

### Ollama (self-hosted)

- **API key**: Leave blank
- **Model name**: `gemma3:4b` (or any model you have pulled)
- **Base URL**: `http://localhost:11434/v1`
- **Allowed tags**: Your tag list

### OpenRouter (multiple providers)

- **API key**: Your OpenRouter API key
- **Model name**: `anthropic/claude-4-5-sonnet` (or any supported model)
- **Base URL**: `https://openrouter.ai/api/v1`
- **Allowed tags**: Your tag list
