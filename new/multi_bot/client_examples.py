import requests
import json

BASE_URL = "http://localhost:8000"

def print_response(response):
    """Pretty print API response."""
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
    print("-" * 80)

# Example 1: Get API health status
def check_health():
    print("\n🔍 Checking API Health")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response)

# Example 2: List available bots
def list_bots():
    print("\n📋 Listing Available Bots")
    response = requests.get(f"{BASE_URL}/bots")
    print_response(response)

# Example 3: Query a bot
def query_bot(bot_name, query):
    print(f"\n❓ Querying {bot_name}")
    payload = {"query": query}
    response = requests.post(f"{BASE_URL}/bots/{bot_name}/query", json=payload)
    print_response(response)

# Example 4: Upload a document
def upload_document(file_path, domain):
    print(f"\n📤 Uploading document to {domain} domain")
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'domain': domain}
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
    print_response(response)

# Example 5: Start document ingestion
def start_ingestion(domain):
    print(f"\n🔄 Starting ingestion for {domain}")
    response = requests.post(f"{BASE_URL}/ingest/{domain}")
    print_response(response)

if __name__ == "__main__":
    # Run examples
    check_health()
    list_bots()
    
    # Uncomment the following examples as needed:
    # upload_document("path/to/your/document.pdf", "ipc")
    # start_ingestion("ipc")
    # query_bot("IPC Bot", "What is the punishment for theft?")
