import os
import streamlit as st
from utils import LegalBotManager
from dotenv import load_dotenv
import logging
import requests

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@st.cache_resource
def initialize_bot_manager():
    """Initialize the bot manager (cached to prevent reinitialization)."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("GOOGLE_API_KEY not found in environment variables!")
        st.stop()
    
    try:
        return LegalBotManager(google_api_key=api_key)
    except Exception as e:
        st.error(f"Error initializing bot manager: {e}")
        st.stop()

# App title
st.title("RAGify India: Multi-Domain Legal Assistant")

# Initialize bot manager
bot_manager = initialize_bot_manager()
available_bots = bot_manager.get_available_bots()

# Check if web voice server is running
web_voice_url = "http://localhost:5002"
web_voice_running = False

try:
    response = requests.get(web_voice_url, timeout=1)
    if response.status_code == 200:
        web_voice_running = True
except:
    web_voice_running = False

# Add voice interface info to sidebar
with st.sidebar.expander("Voice Interface", expanded=True):
    if web_voice_running:
        st.success("Web voice interface is available")
        st.markdown(f"[Open Voice Interface]({web_voice_url})")
        st.markdown("Use your browser's microphone to ask questions without making a phone call")
    else:
        st.warning("Web voice interface is not running")
        st.markdown("To enable voice interface, run: `python web_voice_server.py`")

if not available_bots:
    st.warning("No bots are available. Please ingest documents first.")
    
    st.info("""
    ## How to ingest documents
    
    1. Create folders for each domain under `data/` directory:
       - `data/ipc/` for IPC documents
       - `data/rti/` for RTI documents
       - `data/labor_law/` for Labor Law documents
       - `data/constitution/` for Constitution documents
       
    2. Add PDF or text files to these directories
    
    3. Run the ingestion script:
       ```
       python ingest/ingest_all.py
       ```
       
    Or ingest a specific domain:
       ```
       python ingest/ingest_all.py --domain ipc
       ```
    """)
    st.stop()

# Select bot
selected_bot = st.sidebar.selectbox("Select Legal Domain Bot", available_bots)

# Domain descriptions
domain_descriptions = {
    "IPC Bot": "Specialized in Indian Penal Code (IPC) sections, criminal offenses, and punishments.",
    "RTI Bot": "Expert on Right to Information (RTI) Act, filing procedures, and information access rights.",
    "Labor Law Bot": "Focused on Indian labor regulations, worker's rights, and workplace laws.",
    "Constitution Bot": "Knowledgeable about Indian Constitution, fundamental rights, and governance structure."
}

# Display bot description
if selected_bot in domain_descriptions:
    st.sidebar.info(domain_descriptions[selected_bot])

# Query input
st.subheader(f"Ask {selected_bot} a Question")
query = st.text_input("Enter your legal question:")

if query:
    try:
        with st.spinner(f"Consulting {selected_bot}..."):
            result = bot_manager.query_bot(selected_bot, query)
            
            # Display answer
            st.markdown("### Answer")
            st.write(result["result"])
            
            # Display sources
            if result.get("source_documents"):
                st.markdown("### Sources")
                for i, doc in enumerate(result["source_documents"]):
                    source = doc.metadata.get("source", "Unknown")
                    page = doc.metadata.get("page", "N/A")
                    st.markdown(f"**Source {i+1}**: {source}, Page: {page}")
                    
                    # Display snippet of content
                    with st.expander("View content snippet"):
                        st.markdown(doc.page_content[:500] + "...")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Sidebar information
st.sidebar.header("About")
st.sidebar.markdown("""
This multi-domain legal assistant uses Retrieval Augmented Generation (RAG) to provide 
accurate information about different areas of Indian law.

Each bot specializes in a specific legal domain and has been trained on relevant documents.
""")

# Instructions in sidebar
st.sidebar.header("Instructions")
st.sidebar.markdown("""
1. Select a domain-specific bot from the dropdown
2. Enter your legal question in the text input
3. Wait for the AI to retrieve relevant information and generate an answer
4. Review the answer and the sources used
""")

if __name__ == "__main__":
    # Run with: streamlit run app.py
    pass
