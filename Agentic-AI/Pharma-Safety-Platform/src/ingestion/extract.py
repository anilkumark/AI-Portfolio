"""
Extraction chain: Textract (for scanned/fax docs) -> Comprehend Medical
(entity grounding) -> Bedrock/Claude (schema-constrained extraction).

REQUIRES: AWS credentials with access to Textract, Comprehend Medical,
and Bedrock, plus the model access grant for the Claude model used.
Cannot be executed in this environment — no AWS credentials are
available here. Run locally once your credentials are configured
(AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION, or an
attached IAM role).
"""

import json
import boto3

BEDROCK_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # pin explicitly, never "latest"

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "patient_age": {"type": ["integer", "null"]},
        "patient_sex": {"type": ["string", "null"]},
        "adverse_event_text": {"type": "string"},
        "suspect_product": {"type": "string"},
        "therapy_details": {"type": "object"},
        "concomitant_drugs": {"type": "array", "items": {"type": "string"}},
        "medical_history": {"type": "string"},
        "outcome": {"type": ["string", "null"], "enum": ["death", "recovered", "ongoing", None]},
        "life_threatening_flag": {"type": ["boolean", "null"]},
        "hospitalized": {"type": ["boolean", "null"]},
        "hospitalization_prolonged": {"type": ["boolean", "null"]},
        "disability_flag": {"type": ["boolean", "null"]},
        "congenital_anomaly_flag": {"type": ["boolean", "null"]},
        "field_confidence": {
            "type": "object",
            "description": "Self-reported confidence (0.0-1.0) per field above, "
                            "named identically to the field it scores.",
        },
    },
    "required": ["adverse_event_text", "suspect_product", "field_confidence"],
}

EXTRACTION_SYSTEM_PROMPT = """You are extracting structured adverse-event data from a document that has
already been OCR'd and pre-tagged with medical entities. You are grounding your extraction in the tagged
entities and the raw text provided — you are not diagnosing, advising, or inferring anything not stated
or clearly implied in the source text.

Rules:
1. Populate every field only from what is explicitly stated or unambiguously implied in the source text.
2. If a field cannot be determined from the text, return null for it — never guess.
3. For every field you populate, also populate a corresponding entry in field_confidence with your
   genuine self-assessed confidence from 0.0 to 1.0. A field you are unsure about should get a low score,
   not be omitted.
4. Return ONLY the JSON object matching the provided schema. No prose, no markdown fencing.
"""


def run_textract(s3_bucket: str, s3_key: str) -> dict:
    """Runs Textract AnalyzeDocument with FORMS and TABLES enabled.
    Returns the raw Textract response — table cells retain row/column
    position, checkbox fields return as SELECTED/NOT_SELECTED with a
    confidence score per selection."""
    client = boto3.client("textract")
    response = client.analyze_document(
        Document={"S3Object": {"Bucket": s3_bucket, "Name": s3_key}},
        FeatureTypes=["FORMS", "TABLES"],
    )
    return response


def extract_text_from_textract_response(response: dict) -> str:
    """Flattens Textract's block structure into plain text for the
    Comprehend Medical and Bedrock steps. Table/checkbox structure is
    retained separately (not shown here) for cases where structure
    itself is confidence-relevant."""
    lines = [block["Text"] for block in response.get("Blocks", [])
             if block.get("BlockType") == "LINE" and "Text" in block]
    return "\n".join(lines)


def run_comprehend_medical(text: str) -> list[dict]:
    """Detects medical entities (medications, conditions, PHI) via
    Comprehend Medical. This grounds the Bedrock extraction call with a
    pre-identified entity list rather than asking the model to find
    entities cold in raw prose."""
    client = boto3.client("comprehendmedical")
    response = client.detect_entities_v2(Text=text)
    return response.get("Entities", [])


def run_bedrock_extraction(document_text: str, medical_entities: list[dict]) -> dict:
    """The schema-constrained extraction call. Uses Bedrock's tool-use /
    structured output to force the response into EXTRACTION_SCHEMA shape
    rather than parsing free-form prose."""
    client = boto3.client("bedrock-runtime")

    entities_summary = "\n".join(
        f"- {e.get('Type')}: {e.get('Text')}" for e in medical_entities
    )

    user_message = (
        f"Pre-identified medical entities:\n{entities_summary}\n\n"
        f"Source document text:\n{document_text}"
    )

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "system": EXTRACTION_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
        "tools": [{
            "name": "record_extraction",
            "description": "Record the structured extraction result",
            "input_schema": EXTRACTION_SCHEMA,
        }],
        "tool_choice": {"type": "tool", "name": "record_extraction"},
    }

    response = client.invoke_model(modelId=BEDROCK_MODEL_ID, body=json.dumps(body))
    result = json.loads(response["body"].read())

    for block in result.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == "record_extraction":
            return block["input"]

    raise ValueError("Bedrock response did not contain the expected tool_use block — "
                      "extraction failed to produce structured output")


def extract_case(s3_bucket: str, s3_key: str, local_file_path: str, source_channel: str) -> dict:
    """
    Full extraction chain for one document. Classification decides the
    path — this function no longer accepts a pre-decided is_digital_pdf
    flag from nowhere; it classifies the document itself, using the same
    logic tested in tests/test_pdf_handling.py.
    """
    from src.ingestion.classify import classify_document, DocType
    from src.ingestion.pdf_extract import extract_text_from_pdf

    doc_type = classify_document(local_file_path, source_channel)

    if doc_type == DocType.DIGITAL_PDF:
        document_text = extract_text_from_pdf(local_file_path)
    elif doc_type == DocType.STRUCTURED_FORM:
        # structured forms still go through Textract's FORMS/TABLES mode
        # even when digital, because checkbox and table structure matters
        # more than raw text for these specific templates
        textract_response = run_textract(s3_bucket, s3_key)
        document_text = extract_text_from_textract_response(textract_response)
    else:  # SCANNED_FAX
        textract_response = run_textract(s3_bucket, s3_key)
        document_text = extract_text_from_textract_response(textract_response)

    entities = run_comprehend_medical(document_text)
    extraction = run_bedrock_extraction(document_text, entities)
    extraction["_doc_type"] = doc_type.value  # retained for audit — which path this case took
    return extraction
