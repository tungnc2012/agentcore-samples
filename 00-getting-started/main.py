"""
Customer Support Agent — Bedrock Knowledge Base Edition

This agent retrieves product info, return policies, and promotions from
an Amazon Bedrock Knowledge Base backed by S3 instead of hardcoded data.

Before deploying:
  1. Create a Bedrock Knowledge Base pointing to an S3 bucket
  2. Upload the files from kb-docs/ to that S3 bucket
  3. Sync the Knowledge Base
  4. Set KNOWLEDGE_BASE_ID below (or via environment variable)

Usage:
  1. agentcore create --name CustomerSupport --framework Strands --model-provider Bedrock --defaults
  2. cd CustomerSupport
  3. Copy this file to app/CustomerSupport/main.py
  4. agentcore dev          # test locally
  5. agentcore deploy       # deploy to AWS
  6. agentcore invoke "What products do you have?" --stream
"""

import os
import boto3
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

# --- Bedrock Knowledge Base Configuration ---
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "YOUR_KB_ID")

bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")


def _query_kb(query: str, num_results: int = 5) -> str:
    """Query the Bedrock Knowledge Base and return concatenated results."""
    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": num_results
                }
            },
        )
        results = []
        for result in response.get("retrievalResults", []):
            text = result.get("content", {}).get("text", "").strip()
            if text:
                results.append(text)
        if results:
            return "\n---\n".join(results)
        return "No relevant information found in the knowledge base."
    except Exception as e:
        log.error(f"KB retrieval error: {e}")
        return f"Error retrieving information: {e}"


# --- Tools ---

@tool
def search_products(query: str) -> str:
    """Search for product information by name, ID, category, or keyword.

    Use this tool when the customer asks about products, pricing, features,
    availability, warranty, or wants to browse the catalog.

    Args:
        query: Product name, ID (e.g., 'PROD-001'), category, or search keyword

    Returns:
        Product details from the knowledge base
    """
    return _query_kb(f"product information: {query}")


@tool
def search_return_policy(topic: str) -> str:
    """Look up return and refund policy information.

    Use this tool when the customer asks about returns, refunds, exchanges,
    return windows, return conditions, or how to initiate a return.

    Args:
        topic: The return policy topic or product category
               (e.g., 'electronics return policy', 'how to return', 'refund timeline')

    Returns:
        Return policy details from the knowledge base
    """
    return _query_kb(f"return policy: {topic}")


@tool
def search_promotions(query: str) -> str:
    """Look up current promotions, promo codes, and bulk purchase discounts.

    Use this tool when the customer asks about deals, discounts, promo codes,
    bulk pricing, or ways to save money.

    Args:
        query: Promotion topic, category, or promo code
               (e.g., 'electronics discounts', 'SUMMER2026', 'bulk discount')

    Returns:
        Promotion and discount details from the knowledge base
    """
    return _query_kb(f"promotions and discounts: {query}")


@tool
def calculate_bulk_price(product_id: str, quantity: int) -> str:
    """Calculate the total price for a bulk purchase including any volume discount.

    Use this tool when the customer wants to know the price for buying multiple
    units of the same product.

    Args:
        product_id: The product ID (e.g., 'PROD-001')
        quantity: Number of units to purchase (must be >= 1)

    Returns:
        Price breakdown with discount tier and total
    """
    if quantity < 1:
        return "Quantity must be at least 1."

    product_info = _query_kb(f"product {product_id} price", num_results=1)

    discount_pct = 0
    if quantity >= 10:
        discount_pct = 15
    elif quantity >= 5:
        discount_pct = 10
    elif quantity >= 3:
        discount_pct = 5

    return (
        f"Bulk order details for {product_id} x{quantity}:\n"
        f"Product info from catalog:\n{product_info}\n\n"
        f"Bulk discount tier: {discount_pct}% "
        f"({'no discount — minimum 3 units for 5% off' if discount_pct == 0 else f'for {quantity}+ units'})\n"
        f"Note: Apply the {discount_pct}% discount to the unit price shown above to calculate the final total."
    )


# --- Agent Setup ---

SYSTEM_PROMPT = """You are a helpful and professional customer support assistant for an e-commerce company.

Your role is to:
- Provide accurate information by searching the knowledge base using your tools
- Be friendly, patient, and understanding with customers
- Proactively mention relevant promotions or bulk discounts when appropriate
- Always offer additional help after answering questions

You have access to:
1. search_products() - Search the product catalog for info, pricing, features, warranty
2. search_return_policy() - Look up return and refund policies
3. search_promotions() - Find active promo codes and bulk discount info
4. calculate_bulk_price() - Calculate total price for bulk orders with volume discounts

Always use the appropriate tool to look up information rather than guessing.
If a tool returns no results, let the customer know and offer to help differently."""

_agent = None


def get_or_create_agent():
    global _agent
    if _agent is None:
        _agent = Agent(
            model=load_model(),
            system_prompt=SYSTEM_PROMPT,
            tools=[search_products, search_return_policy, search_promotions, calculate_bulk_price],
        )
    return _agent


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent...")
    agent = get_or_create_agent()
    stream = agent.stream_async(payload.get("prompt"))
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
