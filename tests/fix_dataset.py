# fix_datasets.py
from langsmith import Client
from tests.cases import DRAFT_TESTS, TRIAGE_TESTS
import os
from dotenv import load_dotenv

load_dotenv()

client = Client()

def reset_dataset(name, inputs, outputs):
    # 1. Delete if exists
    if client.has_dataset(dataset_name=name):
        print(f"🗑️  Deleting existing '{name}'...")
        client.delete_dataset(dataset_name=name)
    
    # 2. Create fresh
    print(f"✨ Creating '{name}'...")
    dataset = client.create_dataset(dataset_name=name)
    
    # 3. Upload examples
    client.create_examples(
        inputs=inputs,
        outputs=outputs,
        dataset_id=dataset.id,
    )
    print(f"✅ Uploaded {len(inputs)} examples to '{name}'")

if __name__ == "__main__":
    # Prepare Triage Data
    triage_inputs = [{"email": x["email"]} for x in TRIAGE_TESTS]
    triage_outputs = [{"expected": x["expected"]} for x in TRIAGE_TESTS]
    
    # Prepare Draft Data

    draft_inputs = [x["inputs"] for x in DRAFT_TESTS]

    draft_outputs = [x["expected"] for x in DRAFT_TESTS]


    # Run Reset
    reset_dataset("Email Triage Dataset", triage_inputs, triage_outputs)
    reset_dataset("Email Draft Dataset", draft_inputs, draft_outputs)