import os

import pandas as pd
import chromadb
import vertexai
from vertexai.language_models import TextEmbeddingModel

PROJECT_ID = "hospital-verification-agent"
LOCATION = "us-central1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "medical_records.csv")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_store")

vertexai.init(project=PROJECT_ID, location=LOCATION)
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

df = pd.read_csv(CSV_PATH)

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection("medical_records")

for i, row in df.iterrows():
    text = f"{row['diagnosis']}. {row['doctor_notes']}"
    embedding = embedding_model.get_embeddings([text])[0].values
    collection.add(
        ids=[str(i)],
        embeddings=[embedding],
        metadatas=[
            {
                "patient_name": row["patient_name"],
                "diagnosis": row["diagnosis"],
                "treatment_date": row["treatment_date"],
            }
        ],
        documents=[text],
    )

print(f"Stored {len(df)} records in Chroma vector store at {CHROMA_PATH}")
