# Stock Price Retrieval Issue - Root Cause & Fix

## Issue Description

The AI agent failed to retrieve current stock prices for Apple (AAPL), Microsoft (MSFT), and Google (GOOGL), returning the error message:

> "It looks like I wasn't able to retrieve the current stock prices for Apple (AAPL), Microsoft (MSFT), and Google (GOOGL) at this moment."

## Root Cause Analysis

The agent incorrectly attempted to use the `crypto_price` tool to fetch stock prices instead of using the AlphaVantage MCP server tools.

### Why This Happened

1. **Ambiguous Tool Description**: The `crypto_price` tool description was:
   ```python
   "Get current cryptocurrency prices. Useful when user asks about Bitcoin, Ethereum, or other crypto prices."
   ```
   This didn't explicitly state that it's ONLY for cryptocurrencies and NOT for stocks.

2. **Insufficient Guidance in Agent Prompt**: The agent's decision-making prompt listed tools but didn't clearly distinguish:
   - `crypto_price` → ONLY for cryptocurrencies (BTC, ETH, DOGE, etc.)
   - `AlphaVantage tools` → For stock prices (AAPL, MSFT, GOOGL, TSLA, etc.)

3. **Tool Selection Confusion**: The LLM saw "prices" in both contexts and incorrectly chose `crypto_price` for stock symbols, which are NOT supported by the CoinGecko API (crypto-only API).

### Technical Details

- **File**: `backend/services/tools.py` (line 182)
- **Class**: `CryptoPriceTool`
- **Client**: `CoinGeckoCryptoClient` (uses CoinGecko API)
- **Limitation**: CoinGecko API only supports cryptocurrencies, not traditional stock symbols

## The Fix

### Changes Made

#### 1. Updated `CryptoPriceTool` Description ([tools.py](../backend/services/tools.py#L182))

**Before**:
```python
self.description = "Get current cryptocurrency prices. Useful when user asks about Bitcoin, Ethereum, or other crypto prices."
```

**After**:
```python
self.description = "Get current cryptocurrency prices ONLY (Bitcoin, Ethereum, Dogecoin, etc.). DO NOT use for stock prices (AAPL, MSFT, GOOGL, TSLA, etc.) - use AlphaVantage tools for stocks."
```

#### 2. Updated Agent Decision Prompt ([agent.py](../backend/services/agent.py#L394))

**Before**:
```python
"- crypto_price: Get cryptocurrency prices (params: symbol, fiat)"
```

**After**:
```python
"- crypto_price: Get CRYPTOCURRENCY prices ONLY like BTC, ETH (params: symbol, fiat) - DO NOT use for STOCKS"
```

#### 3. Enhanced AlphaVantage Tools Section ([agent.py](../backend/services/agent.py#L402))

**Before**:
```python
available_tools_list.append("\n📊 AlphaVantage Financial & Market Data Tools:")
```

**After**:
```python
available_tools_list.append("\n📊 AlphaVantage Financial & Market Data Tools (USE THESE FOR STOCK PRICES like AAPL, MSFT, GOOGL, TSLA):")
```

#### 4. Added Explicit Rules ([agent.py](../backend/services/agent.py#L432))

**New rules added**:
```python
6. For STOCK prices (AAPL, MSFT, GOOGL, TSLA, etc.), use AlphaVantage tools like GLOBAL_QUOTE, NOT crypto_price
7. For CRYPTOCURRENCY prices (BTC, ETH, DOGE, etc.), use crypto_price tool
```

## How It Works Now

1. **User asks for stock prices** (e.g., "What's the price of AAPL, MSFT, GOOGL?")
2. **Agent reads the updated prompt** with clear guidance:
   - Sees `crypto_price` is ONLY for crypto (BTC, ETH)
   - Sees AlphaVantage tools are for STOCKS (AAPL, MSFT, GOOGL)
3. **Agent selects the correct tool**: AlphaVantage `GLOBAL_QUOTE` tool
4. **MCP client calls AlphaVantage API** with the stock symbol
5. **Returns accurate stock price data** to the user

## Example: Correct Tool Selection

### Request
```
"What are the current stock prices for Apple (AAPL), Microsoft (MSFT), and Google (GOOGL)?"
```

### Agent Decision (Now)
```json
{
  "action": "call_tools_parallel",
  "tools": [
    {"tool_name": "GLOBAL_QUOTE", "arguments": {"symbol": "AAPL"}},
    {"tool_name": "GLOBAL_QUOTE", "arguments": {"symbol": "MSFT"}},
    {"tool_name": "GLOBAL_QUOTE", "arguments": {"symbol": "GOOGL"}}
  ],
  "reasoning": "fetch multiple stock prices simultaneously using AlphaVantage tools"
}
```

## Testing

To verify the fix:

1. **Start the application**:
   ```bash
   cd /Users/adriangulyas/Development/robotdreams/ai_agent_complex
   ./start-dev.sh
   ```

2. **Test stock price query**:
   ```
   User: "What are the current prices for AAPL, MSFT, and GOOGL?"
   ```

3. **Expected behavior**:
   - Agent should use AlphaVantage `GLOBAL_QUOTE` tool (NOT `crypto_price`)
   - Returns current stock prices for all three symbols

4. **Test crypto price query** (ensure crypto still works):
   ```
   User: "What's the current price of Bitcoin and Ethereum?"
   ```

5. **Expected behavior**:
   - Agent should use `crypto_price` tool
   - Returns current BTC and ETH prices

## Prevention

To prevent similar issues in the future:

1. **Be explicit in tool descriptions**: Always specify what the tool does AND what it doesn't do
2. **Add examples in descriptions**: Include specific examples (BTC vs AAPL)
3. **Use clear agent prompt rules**: Add numbered rules for tool selection
4. **Test edge cases**: Test with both stocks and crypto to ensure correct routing

## Related Files

- [backend/services/tools.py](../backend/services/tools.py) - Tool definitions
- [backend/services/agent.py](../backend/services/agent.py) - Agent decision logic
- [backend/infrastructure/tool_clients.py](../backend/infrastructure/tool_clients.py) - API clients
- [backend/main.py](../backend/main.py) - Application initialization

## Summary

**Root Cause**: Ambiguous tool descriptions led the LLM to incorrectly select the `crypto_price` tool (CoinGecko API) for stock symbols (AAPL, MSFT, GOOGL), which only supports cryptocurrencies.

**Fix**: Added explicit guidance in tool descriptions and agent prompts to clearly distinguish:
- `crypto_price` → Cryptocurrencies ONLY (BTC, ETH, DOGE, etc.)
- `AlphaVantage tools` → Stocks ONLY (AAPL, MSFT, GOOGL, TSLA, etc.)

**Result**: Agent now correctly selects AlphaVantage tools for stock prices and crypto_price tool for cryptocurrency prices.
