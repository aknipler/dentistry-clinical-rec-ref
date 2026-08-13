from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.config import get_secret

# llama_index's OpenAI embedding reads the key from this env var
os.environ["OPENAI_API_KEY"] = get_secret("OPENAI_API_KEY")

# Find the files
input_files = []
dir_path = Path(os.path.dirname(os.path.realpath(__file__))).parent / "reference_data"
print("Files found:")
for file in Path(dir_path).glob("*"):
    input_files.append(file)
    print(file)

# Load the files into LlamaIndex
print("Loading Files")
reader = SimpleDirectoryReader(input_files=input_files)
documents = reader.load_data()

# Create and Save the index
print("Saving Index")
index = VectorStoreIndex.from_documents(documents)
index.storage_context.persist(persist_dir="storage")


