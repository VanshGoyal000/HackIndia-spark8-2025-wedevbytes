import argparse
import logging
from domain_ingestion import (
    IPCDocumentIngestion,
    RTIDocumentIngestion,
    LaborLawDocumentIngestion,
    ConstitutionDocumentIngestion
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ingest_all_domains():
    """Ingest documents for all domains."""
    domains = [
        IPCDocumentIngestion(),
        RTIDocumentIngestion(),
        LaborLawDocumentIngestion(),
        ConstitutionDocumentIngestion()
    ]
    
    for domain_ingestor in domains:
        logger.info(f"Processing {domain_ingestor.domain_name} domain")
        domain_ingestor.ingest()
    
    logger.info("All domains processed successfully")

def ingest_specific_domain(domain):
    """Ingest documents for a specific domain."""
    domain_mapping = {
        "ipc": IPCDocumentIngestion(),
        "rti": RTIDocumentIngestion(),
        "labor_law": LaborLawDocumentIngestion(),
        "constitution": ConstitutionDocumentIngestion()
    }
    
    if domain in domain_mapping:
        logger.info(f"Processing {domain} domain")
        domain_mapping[domain].ingest()
        logger.info(f"{domain} domain processed successfully")
    else:
        logger.error(f"Unknown domain: {domain}")
        print(f"Available domains: {', '.join(domain_mapping.keys())}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents for legal domains")
    parser.add_argument("--domain", type=str, help="Specific domain to ingest (ipc, rti, labor_law, constitution)")
    
    args = parser.parse_args()
    
    if args.domain:
        ingest_specific_domain(args.domain)
    else:
        ingest_all_domains()
