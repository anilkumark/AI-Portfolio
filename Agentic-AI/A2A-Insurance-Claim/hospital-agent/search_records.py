import os

import chromadb
import vertexai
from vertexai.language_models import TextEmbeddingModel

PROJECT_ID = "hospital-verification-agent"
LOCATION = "us-central1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_store")

vertexai.init(project=PROJECT_ID, location=LOCATION)
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection("medical_records")


def search_claim(claimed_injury_description, patient_name, top_k=1):
    print("\n[search_claim] STEP 1 - input received:")
    print(f"    claimed_injury_description = {claimed_injury_description!r}")
    print(f"    patient_name                = {patient_name!r}")

    query_embedding = embedding_model.get_embeddings([claimed_injury_description])[
        0
    ].values
    print(f"\n[search_claim] STEP 2 - text converted to embedding vector via Vertex AI text-embedding-004")
    print(f"    vector length = {len(query_embedding)}")
    print(f"    first 5 values = {list(query_embedding)[:5]}")

    print(f"\n[search_claim] STEP 3 - querying Chroma collection 'medical_records'")
    print(f"    filter: where patient_name == {patient_name!r}")
    print(f"    asking for top_k = {top_k} closest match(es) by vector distance")
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"patient_name": patient_name},  # only search this patient's own records
    )

    print(f"\n[search_claim] STEP 4 - raw Chroma result:")
    print(f"    ids        = {results['ids']}")
    print(f"    metadatas  = {results['metadatas']}")
    print(f"    documents  = {results['documents']}")
    print(f"    distances  = {results['distances']}")
    if not results["metadatas"][0]:
        print(f"    -> EMPTY: no record exists in the DB for patient_name={patient_name!r}")
    else:
        print(f"    -> closest match distance = {results['distances'][0][0]} (lower = more similar in meaning)")

    return results


if __name__ == "__main__":
    print("=" * 70)
    print("FLOW: this simulates the Hospital Agent searching its own medical")
    print("records for a claim, using semantic (meaning-based) search instead")
    print("of exact keyword matching.")
    print("=" * 70)
    result = search_claim(
        "patient reported neck pain after being rear-ended", "John Doe"
    )
    print("\nFINAL RETURN VALUE:", result)
