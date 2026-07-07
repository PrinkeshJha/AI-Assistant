import os
import json
from sentence_transformers import SentenceTransformer, util

_shared_model = None

def get_shared_model():
    global _shared_model
    if _shared_model is None:
        _shared_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _shared_model

class EmbeddingClassifier:
    def __init__(self, intents_dir="intents"):
        self.model = get_shared_model()
        self.intents_dir = intents_dir
        self.intent_embeddings = {} # Maps intent_name -> np.array of embeddings
        self.intent_examples = {}   # Maps intent_name -> list of example phrases
        self._load_and_encode_intents()

    def _load_and_encode_intents(self):
        if not os.path.exists(self.intents_dir):
            os.makedirs(self.intents_dir, exist_ok=True)
            print(f"Intents directory '{self.intents_dir}' created. Please add intent JSON files.")
            return

        for filename in os.listdir(self.intents_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.intents_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    intent_name = data.get("intent")
                    examples = data.get("examples", [])
                    if intent_name and examples:
                        # Precompute embeddings
                        embeddings = self.model.encode(examples, convert_to_tensor=True)
                        self.intent_embeddings[intent_name] = embeddings
                        self.intent_examples[intent_name] = examples
                        print(f"Loaded and encoded {len(examples)} examples for intent '{intent_name}'.")
                except Exception as e:
                    print(f"Error loading intent file {filename}: {e}")

    def classify(self, query: str) -> dict:
        """
        Classifies the query and returns a dictionary mapping intent names to similarity scores.
        Similarity score for an intent is the MAXIMUM similarity score between the query
        and any of the example phrases for that intent.
        """
        if not self.intent_embeddings:
            return {}

        query_embedding = self.model.encode(query, convert_to_tensor=True)
        scores = {}

        for intent_name, examples_embeddings in self.intent_embeddings.items():
            # Compute cosine similarity
            similarities = util.cos_sim(query_embedding, examples_embeddings)[0]
            # Convert to float and take the maximum
            max_score = float(similarities.max().item())
            
            # Calibration: scale up raw scores that reflect clear matching intent
            # all-MiniLM-L6-v2 cosine similarities typically range 0.2 to 0.8.
            # We map:
            # max_score >= 0.50 -> maps to 0.65+
            # max_score >= 0.40 -> maps to 0.50+
            if max_score >= 0.50:
                confidence = 0.65 + (max_score - 0.50) * 0.70
            elif max_score >= 0.40:
                confidence = 0.50 + (max_score - 0.40) * 1.50
            else:
                confidence = max_score
                
            scores[intent_name] = max(0.0, min(1.0, confidence))

        return scores
