# OpenAI Embeddings REST API - Complete Developer Guide

## Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [API Endpoint](#api-endpoint)
- [Request Format](#request-format)
- [Request Parameters](#request-parameters)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Code Examples](#code-examples)
- [Best Practices](#best-practices)
- [Rate Limits & Pricing](#rate-limits--pricing)
- [Available Models](#available-models)

---

## Overview

The OpenAI Embeddings API converts text into numerical vector representations (embeddings) that capture semantic meaning. These embeddings are useful for:

- **Semantic search** - Finding similar text based on meaning
- **Clustering** - Grouping related content
- **Recommendations** - Suggesting similar items
- **Anomaly detection** - Identifying outliers
- **Classification** - Categorizing text

**Base URL**: `https://api.openai.com/v1`

---

## Authentication

All requests to the OpenAI API require authentication via an API key.

### HTTP Header
```
Authorization: Bearer YOUR_API_KEY
```

### Obtaining an API Key
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Navigate to API Keys section
3. Create a new secret key
4. Store it securely (it won't be shown again)

⚠️ **Security**: Never expose your API key in client-side code or public repositories.

---

## API Endpoint

### Embeddings Endpoint
```
POST https://api.openai.com/v1/embeddings
```

---

## Request Format

### HTTP Headers
| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes |
| `Authorization` | `Bearer YOUR_API_KEY` | Yes |
| `OpenAI-Organization` | Your organization ID | No |

### Request Body
The request body must be a JSON object with the following structure:

```json
{
  "input": "Your text to embed",
  "model": "text-embedding-3-small",
  "encoding_format": "float",
  "dimensions": 1536,
  "user": "user-123"
}
```

---

## Request Parameters

### Required Parameters

#### `input` (string or array)
The text to generate embeddings for.

- **Type**: `string` or `array of strings`
- **Required**: Yes
- **Maximum tokens**: 8191 tokens for most models
- **Examples**:
  ```json
  "input": "The quick brown fox jumps over the lazy dog"
  ```
  ```json
  "input": ["First text", "Second text", "Third text"]
  ```

**Notes**:
- For multiple inputs, you can pass an array of strings
- Each input will be embedded separately
- Batch requests are more efficient than individual requests
- Empty strings will result in an error

#### `model` (string)
The embedding model to use.

- **Type**: `string`
- **Required**: Yes
- **Available models**:
  - `text-embedding-3-small` - Latest, efficient model (1536 dimensions by default)
  - `text-embedding-3-large` - Latest, most capable model (3072 dimensions by default)
  - `text-embedding-ada-002` - Legacy model (1536 dimensions)

**Example**:
```json
"model": "text-embedding-3-small"
```

**Choosing a model**:
- **text-embedding-3-small**: Best for most use cases, cost-effective
- **text-embedding-3-large**: Higher accuracy, better for complex tasks
- **text-embedding-ada-002**: Legacy compatibility

---

### Optional Parameters

#### `encoding_format` (string)
Format of the returned embedding vectors.

- **Type**: `string`
- **Required**: No
- **Default**: `float`
- **Options**:
  - `float` - Standard floating-point numbers (default)
  - `base64` - Base64-encoded format (more compact for transmission)

**Example**:
```json
"encoding_format": "float"
```

**When to use**:
- Use `float` for standard applications (easier to work with)
- Use `base64` when minimizing bandwidth is critical

#### `dimensions` (integer)
The number of dimensions in the output embeddings.

- **Type**: `integer`
- **Required**: No
- **Default**: Model-specific (1536 for 3-small, 3072 for 3-large)
- **Valid range**: Model-dependent
- **Only supported**: `text-embedding-3-small` and `text-embedding-3-large`

**Example**:
```json
"dimensions": 512
```

**Use cases**:
- Reduce storage and computation costs by using fewer dimensions
- Trade-off: Lower dimensions = less semantic information retained
- Useful when storage/memory is constrained
- Minimum recommended: 256 dimensions

**Note**: Not all models support custom dimensions. Legacy models have fixed dimensionality.

#### `user` (string)
A unique identifier for the end-user making the request.

- **Type**: `string`
- **Required**: No
- **Maximum length**: Not specified
- **Purpose**: Helps OpenAI detect and prevent abuse

**Example**:
```json
"user": "user-12345"
```

**Best practices**:
- Use anonymized user IDs
- Don't include personally identifiable information
- Useful for monitoring and rate limiting per user

---

## Response Format

### Success Response

**HTTP Status**: `200 OK`

**Response Body**:
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [
        0.0023064255,
        -0.009327292,
        -0.0028842222,
        ...
      ]
    }
  ],
  "model": "text-embedding-3-small",
  "usage": {
    "prompt_tokens": 8,
    "total_tokens": 8
  }
}
```

### Response Fields

#### `object` (string)
Type of object returned. Always `"list"` for embeddings.

#### `data` (array)
Array of embedding objects, one for each input.

**Each embedding object contains**:
- `object` (string): Always `"embedding"`
- `index` (integer): Position in the input array (0-indexed)
- `embedding` (array): The embedding vector as an array of floats

#### `model` (string)
The model used to generate embeddings.

#### `usage` (object)
Token usage statistics:
- `prompt_tokens` (integer): Number of tokens in the input
- `total_tokens` (integer): Total tokens used (same as prompt_tokens for embeddings)

### Example with Multiple Inputs

**Request**:
```json
{
  "input": ["Hello world", "Goodbye world"],
  "model": "text-embedding-3-small"
}
```

**Response**:
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.002, -0.009, ...]
    },
    {
      "object": "embedding",
      "index": 1,
      "embedding": [0.001, -0.007, ...]
    }
  ],
  "model": "text-embedding-3-small",
  "usage": {
    "prompt_tokens": 6,
    "total_tokens": 6
  }
}
```

---

## Error Handling

### Common HTTP Status Codes

| Status Code | Meaning | Common Causes |
|-------------|---------|---------------|
| `400 Bad Request` | Invalid request | Malformed JSON, invalid parameters |
| `401 Unauthorized` | Authentication failed | Invalid or missing API key |
| `403 Forbidden` | Permission denied | Insufficient permissions |
| `429 Too Many Requests` | Rate limit exceeded | Too many requests in time window |
| `500 Internal Server Error` | Server error | Temporary OpenAI service issue |
| `503 Service Unavailable` | Service overloaded | High traffic, retry with backoff |

### Error Response Format

```json
{
  "error": {
    "message": "Invalid API key provided",
    "type": "invalid_request_error",
    "param": null,
    "code": "invalid_api_key"
  }
}
```

### Error Types

- `invalid_request_error` - Problem with request format or parameters
- `authentication_error` - Invalid API key
- `permission_error` - Insufficient permissions
- `rate_limit_error` - Too many requests
- `server_error` - OpenAI server issue

### Handling Errors in Code

```python
import requests
import time

def get_embedding_with_retry(text, api_key, max_retries=3):
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": text,
        "model": "text-embedding-3-small"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()["data"][0]["embedding"]
            elif response.status_code == 429:
                # Rate limit - exponential backoff
                wait_time = 2 ** attempt
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            elif response.status_code >= 500:
                # Server error - retry
                print(f"Server error. Retrying... ({attempt + 1}/{max_retries})")
                time.sleep(1)
            else:
                # Client error - don't retry
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(1)
    
    raise Exception("Max retries exceeded")
```

---

## Code Examples

### Python with `requests`

```python
import requests

def get_embedding(text, api_key, model="text-embedding-3-small"):
    """Get embedding using raw HTTP request."""
    url = "https://api.openai.com/v1/embeddings"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "input": text,
        "model": model
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    data = response.json()
    return data["data"][0]["embedding"]

# Usage
api_key = "sk-..."
embedding = get_embedding("Hello, world!", api_key)
print(f"Embedding dimension: {len(embedding)}")
```

### JavaScript (Node.js)

```javascript
async function getEmbedding(text, apiKey, model = "text-embedding-3-small") {
    const url = "https://api.openai.com/v1/embeddings";
    
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${apiKey}`
        },
        body: JSON.stringify({
            input: text,
            model: model
        })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.data[0].embedding;
}

// Usage
const apiKey = "sk-...";
const embedding = await getEmbedding("Hello, world!", apiKey);
console.log(`Embedding dimension: ${embedding.length}`);
```

### cURL

```bash
curl https://api.openai.com/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "input": "Your text here",
    "model": "text-embedding-3-small"
  }'
```

### Batch Processing

```python
def get_embeddings_batch(texts, api_key, model="text-embedding-3-small"):
    """Get embeddings for multiple texts in one request."""
    url = "https://api.openai.com/v1/embeddings"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "input": texts,  # Array of strings
        "model": model
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    data = response.json()
    
    # Sort by index to maintain order
    embeddings = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in embeddings]

# Usage
texts = ["First text", "Second text", "Third text"]
embeddings = get_embeddings_batch(texts, api_key)
```

---

## Best Practices

### 1. Batch Requests
- Embed multiple texts in a single API call (up to 2048 inputs)
- Reduces latency and costs
- More efficient than individual requests

### 2. Caching
- Cache embeddings to avoid redundant API calls
- Embeddings for the same text and model are deterministic
- Store embeddings in a database or file system

### 3. Text Preprocessing
- Remove unnecessary whitespace
- Normalize text (lowercase, remove special characters) if needed
- Truncate or chunk long texts to stay within token limits

### 4. Error Handling
- Implement exponential backoff for rate limits
- Retry on temporary server errors (5xx)
- Don't retry on client errors (4xx)

### 5. Token Management
- Monitor token usage in responses
- Be aware of model-specific token limits
- Use tokenizer libraries to estimate costs before API calls

### 6. Model Selection
- Start with `text-embedding-3-small` for prototyping
- Upgrade to `text-embedding-3-large` if accuracy is critical
- Consider custom dimensions to reduce costs

### 7. Security
- Never expose API keys in client-side code
- Use environment variables for keys
- Rotate keys regularly
- Set usage limits in OpenAI dashboard

---

## Rate Limits & Pricing

### Rate Limits (as of Dec 2025)

Rate limits vary by organization tier. Example limits:

| Tier | Requests/min | Tokens/min |
|------|--------------|------------|
| Free | 3 | 150,000 |
| Tier 1 | 500 | 1,000,000 |
| Tier 2 | 5,000 | 5,000,000 |
| Tier 3+ | Higher | Higher |

**Note**: Check [platform.openai.com/account/limits](https://platform.openai.com/account/limits) for your current limits.

### Pricing (per 1M tokens)

| Model | Price |
|-------|-------|
| text-embedding-3-small | $0.02 |
| text-embedding-3-large | $0.13 |
| text-embedding-ada-002 | $0.10 |

**Cost calculation**:
```
Cost = (Number of tokens / 1,000,000) × Price per 1M tokens
```

**Example**:
- 100,000 tokens with `text-embedding-3-small`
- Cost: (100,000 / 1,000,000) × $0.02 = $0.002

---

## Available Models

### text-embedding-3-small
- **Dimensions**: 1536 (default, customizable)
- **Performance**: Strong performance for most use cases
- **Cost**: $0.02 / 1M tokens
- **Best for**: General-purpose embeddings, cost-sensitive applications

### text-embedding-3-large
- **Dimensions**: 3072 (default, customizable)
- **Performance**: Highest quality embeddings
- **Cost**: $0.13 / 1M tokens
- **Best for**: High-accuracy requirements, complex semantic tasks

### text-embedding-ada-002 (Legacy)
- **Dimensions**: 1536 (fixed)
- **Performance**: Good, but superseded by v3 models
- **Cost**: $0.10 / 1M tokens
- **Best for**: Legacy compatibility

### Model Comparison

| Feature | 3-small | 3-large | ada-002 |
|---------|---------|---------|---------|
| Max tokens | 8191 | 8191 | 8191 |
| Dimensions | 1536 (custom) | 3072 (custom) | 1536 (fixed) |
| Custom dimensions | ✅ | ✅ | ❌ |
| Performance | Good | Excellent | Good |
| Cost | Lowest | Highest | Medium |

---

## Advanced Topics

### Cosine Similarity

Calculate similarity between embeddings:

```python
import numpy as np

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2)

# Usage
similarity = cosine_similarity(embedding1, embedding2)
# Returns value between -1 and 1 (1 = identical, 0 = orthogonal, -1 = opposite)
```

### Dimensionality Reduction

```python
# Request reduced dimensions
payload = {
    "input": "Your text",
    "model": "text-embedding-3-small",
    "dimensions": 512  # Reduced from default 1536
}

# Smaller storage, faster computation, slightly lower accuracy
```

### Chunking Long Texts

```python
def chunk_text(text, max_tokens=8000):
    """Split long text into chunks."""
    # Simple word-based chunking (use tiktoken for accurate token counting)
    words = text.split()
    chunks = []
    current_chunk = []
    current_count = 0
    
    for word in words:
        word_tokens = len(word) // 4 + 1  # Rough estimate
        if current_count + word_tokens > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_count = word_tokens
        else:
            current_chunk.append(word)
            current_count += word_tokens
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks
```

---

## Troubleshooting

### Common Issues

**Issue**: "Invalid API key"
- **Solution**: Verify API key is correct and active
- Check for extra whitespace or quotes

**Issue**: "Rate limit exceeded"
- **Solution**: Implement exponential backoff
- Upgrade organization tier if needed

**Issue**: "This model's maximum context length is 8191 tokens"
- **Solution**: Chunk long texts before embedding
- Use token counter to verify length

**Issue**: Embeddings seem random or inconsistent
- **Solution**: Embeddings are deterministic for the same input
- Check if you're comparing embeddings from different models

**Issue**: High latency
- **Solution**: Use batch requests for multiple texts
- Consider geographic proximity to API servers

---

## Additional Resources

- **Official Documentation**: [platform.openai.com/docs/guides/embeddings](https://platform.openai.com/docs/guides/embeddings)
- **API Reference**: [platform.openai.com/docs/api-reference/embeddings](https://platform.openai.com/docs/api-reference/embeddings)
- **Community Forum**: [community.openai.com](https://community.openai.com)
- **Status Page**: [status.openai.com](https://status.openai.com)

---

## Version History

- **v3 (2024)**: Introduction of text-embedding-3-small and text-embedding-3-large with custom dimensions
- **v2 (2022)**: text-embedding-ada-002 became the standard
- **v1 (2021)**: Initial embedding models

---

*Last Updated: December 2025*
