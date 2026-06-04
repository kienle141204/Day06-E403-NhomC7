"""Drug data service for local medication lookup."""
import json
import unicodedata
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from rapidfuzz import fuzz, process

from app.config import DATA_PATH, FUZZY_ACCEPT_SCORE, FUZZY_REVIEW_SCORE


class DrugDataService:
    def __init__(self):
        self.drug_items: List[Dict] = []
        self.ingredient_dict: Dict[str, Dict] = {}
        self._load_data()
    
    def _load_data(self):
        """Load drug data from JSON file."""
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Auto-detect drug items structure
        self.drug_items = self._extract_drug_items(data)
        
        # Load ingredient dictionary
        if "ingredient_dictionary" in data:
            for item in data["ingredient_dictionary"]:
                key = item.get("key", "")
                if key:
                    self.ingredient_dict[key] = item
    
    def _extract_drug_items(self, data: Any) -> List[Dict]:
        """Auto-detect drug items list from various JSON structures."""
        # Case 1: root is a list
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict) and self._is_drug_item(item)]
        
        # Case 2: root has "items" key
        if isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                return data["items"]
            if "drug_items" in data and isinstance(data["drug_items"], list):
                return data["drug_items"]
            if "drugs" in data and isinstance(data["drugs"], list):
                return data["drugs"]
            
            # Case 3: scan root values for list of dicts with drug fields
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    if self._is_drug_item(value[0]):
                        return value
        
        return []
    
    def _is_drug_item(self, item: Any) -> bool:
        """Check if item looks like a drug item."""
        if not isinstance(item, dict):
            return False
        return any(field in item for field in ["raw_left", "raw_line", "ingredient_en", "matched_ingredient_key"])
    
    def _normalize_text(self, text: str) -> str:
        """Normalize Vietnamese text for comparison."""
        if not text:
            return ""
        # Lowercase
        text = text.lower()
        # Remove accents (normalize unicode)
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        # Remove special characters
        text = re.sub(r"[^\w\s]", " ", text)
        # Normalize whitespace
        text = " ".join(text.split())
        return text
    
    def _create_searchable_text(self, item: Dict) -> str:
        """Create searchable text from drug item."""
        parts = []
        for field in ["raw_left", "raw_line", "ingredient_vi", "ingredient_en", 
                      "matched_ingredient_key", "category_vi", "strength"]:
            value = item.get(field)
            if value:
                parts.append(str(value))
        return " | ".join(parts)
    
    def resolve_local_drug(self, raw_name: str) -> Dict[str, Any]:
        """
        Resolve a drug by name using fuzzy matching.
        
        Returns dict with:
        - found: bool
        - needs_review: bool
        - matched_item: dict or None
        - confidence: float
        - match_score: float
        """
        if not raw_name or not self.drug_items:
            return {
                "found": False,
                "needs_review": False,
                "matched_item": None,
                "confidence": 0.0,
                "match_score": 0.0
            }
        
        normalized_query = self._normalize_text(raw_name)
        
        # Create searchable corpus
        choices = []
        item_map = {}
        for item in self.drug_items:
            searchable = self._create_searchable_text(item)
            if searchable:
                choices.append(searchable)
                item_map[searchable] = item
        
        if not choices:
            return {
                "found": False,
                "needs_review": False,
                "matched_item": None,
                "confidence": 0.0,
                "match_score": 0.0
            }
        
        # Find best match using rapidfuzz
        result = process.extractOne(
            normalized_query,
            choices,
            scorer=fuzz.WRatio
        )
        
        if not result:
            return {
                "found": False,
                "needs_review": False,
                "matched_item": None,
                "confidence": 0.0,
                "match_score": 0.0
            }
        
        best_match, match_score, _ = result
        matched_item = item_map.get(best_match, {})
        
        # Determine if found based on score
        found = match_score >= FUZZY_ACCEPT_SCORE
        needs_review = matched_item.get("needs_review", False) or (not found and match_score >= FUZZY_REVIEW_SCORE)
        
        return {
            "found": found,
            "needs_review": needs_review,
            "matched_item": matched_item,
            "confidence": match_score / 100.0,
            "match_score": match_score
        }
    
    def resolve_to_medication_dict(self, raw_name: str, dosage: str = None, 
                                   frequency: str = None, duration: str = None) -> Dict[str, Any]:
        """Resolve drug and return ResolvedMedication-compatible dict."""
        result = self.resolve_local_drug(raw_name)
        matched_item = result["matched_item"]
        
        if not result["found"] or not matched_item:
            return {
                "raw_name": raw_name,
                "found": False,
                "needs_review": result["needs_review"],
                "confidence": result["confidence"],
                "uses_vi": [],
                "important_notes_vi": ["Chưa tìm thấy thuốc trong dữ liệu nội bộ. Cần hỏi dược sĩ/bác sĩ hoặc kiểm tra lại tên thuốc."],
                "dosage": dosage,
                "frequency": frequency,
                "duration": duration
            }
        
        # Extract source URLs
        source_urls = []
        ingredient_key = matched_item.get("matched_ingredient_key")
        if ingredient_key and ingredient_key in self.ingredient_dict:
            ingredient_data = self.ingredient_dict[ingredient_key]
            source_urls = ingredient_data.get("sources", [])
        else:
            source_urls = matched_item.get("source_urls", [])
        
        return {
            "raw_name": raw_name,
            "found": True,
            "source": "local_database",
            "matched_name": matched_item.get("ingredient_vi") or matched_item.get("ingredient_en"),
            "ingredient_vi": matched_item.get("ingredient_vi"),
            "ingredient_en": matched_item.get("ingredient_en"),
            "category_vi": matched_item.get("category_vi"),
            "uses_vi": matched_item.get("uses_vi", []),
            "important_notes_vi": matched_item.get("important_notes_vi", []),
            "source_urls": source_urls,
            "confidence": result["confidence"],
            "needs_review": result["needs_review"],
            "dosage": dosage,
            "frequency": frequency,
            "duration": duration
        }


# Singleton instance
_drug_data_service: Optional[DrugDataService] = None


def get_drug_data_service() -> DrugDataService:
    """Get singleton drug data service instance."""
    global _drug_data_service
    if _drug_data_service is None:
        _drug_data_service = DrugDataService()
    return _drug_data_service
