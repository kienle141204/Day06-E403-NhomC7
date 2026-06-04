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
        self._choices: List[str] = []
        self._choice_map: Dict[str, Dict] = {}
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
        
        # Build searchable corpus from ingredient_dictionary
        self._build_search_corpus()
    
    def _build_search_corpus(self):
        """Build searchable text corpus for fuzzy matching."""
        self._choices = []
        self._choice_map = {}
        
        # Add ingredient dictionary entries (these are the clean names)
        for key, item in self.ingredient_dict.items():
            searchable = self._create_ingredient_searchable(item)
            self._choices.append(searchable)
            self._choice_map[searchable] = item
        
        # Also add drug_items for raw name matching
        for item in self.drug_items:
            searchable = self._create_item_searchable(item)
            if searchable:
                self._choices.append(searchable)
                self._choice_map[searchable] = item
    
    def _extract_drug_items(self, data: Any) -> List[Dict]:
        """Auto-detect drug items list from various JSON structures."""
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict) and self._is_drug_item(item)]
        
        if isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                return data["items"]
            if "drug_items" in data and isinstance(data["drug_items"], list):
                return data["drug_items"]
            if "drugs" in data and isinstance(data["drugs"], list):
                return data["drugs"]
            
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
        text = text.lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        text = re.sub(r"[^\w\s]", " ", text)
        text = " ".join(text.split())
        return text
    
    def _create_ingredient_searchable(self, item: Dict) -> str:
        """Create searchable text from ingredient dict."""
        parts = []
        for field in ["ingredient_vi", "ingredient_en", "key", "category_vi"]:
            value = item.get(field)
            if value:
                parts.append(str(value))
        return " | ".join(parts)
    
    def _create_item_searchable(self, item: Dict) -> str:
        """Create searchable text from drug item."""
        parts = []
        for field in ["raw_left", "raw_line", "ingredient_vi", "ingredient_en", 
                      "matched_ingredient_key", "category_vi", "strength"]:
            value = item.get(field)
            if value:
                parts.append(str(value))
        return " | ".join(parts) if parts else ""
    
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
        if not raw_name or not self._choices:
            return {
                "found": False,
                "needs_review": False,
                "matched_item": None,
                "confidence": 0.0,
                "match_score": 0.0
            }
        
        normalized_query = self._normalize_text(raw_name)
        
        # Try multiple search strategies
        best_result = None
        
        # Strategy 1: Direct match with partial ratio (better for partial matches)
        result = process.extractOne(
            normalized_query,
            self._choices,
            scorer=fuzz.partial_ratio
        )
        if result:
            best_result = result
        
        # Strategy 2: Token sort ratio (good for reordered words)
        result2 = process.extractOne(
            normalized_query,
            self._choices,
            scorer=fuzz.token_sort_ratio
        )
        if result2 and (not best_result or result2[1] > best_result[1]):
            best_result = result2
        
        # Strategy 3: WRatio (comprehensive)
        result3 = process.extractOne(
            normalized_query,
            self._choices,
            scorer=fuzz.WRatio
        )
        if result3 and (not best_result or result3[1] > best_result[1]):
            best_result = result3
        
        if not best_result:
            return {
                "found": False,
                "needs_review": False,
                "matched_item": None,
                "confidence": 0.0,
                "match_score": 0.0
            }
        
        best_match, match_score, _ = best_result
        matched_item = self._choice_map.get(best_match, {})
        
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
        
        # Check if it's an ingredient_dict item or drug_item
        if "key" in matched_item:
            # It's from ingredient_dictionary
            return {
                "raw_name": raw_name,
                "found": True,
                "source": "ingredient_dictionary",
                "matched_name": matched_item.get("ingredient_vi"),
                "ingredient_vi": matched_item.get("ingredient_vi"),
                "ingredient_en": matched_item.get("ingredient_en"),
                "category_vi": matched_item.get("category_vi"),
                "uses_vi": matched_item.get("uses_vi", []),
                "important_notes_vi": matched_item.get("important_notes_vi", []),
                "source_urls": matched_item.get("sources", []),
                "confidence": result["confidence"],
                "needs_review": result["needs_review"],
                "dosage": dosage,
                "frequency": frequency,
                "duration": duration
            }
        else:
            # It's from drug_items
            source_urls = matched_item.get("source_urls", [])
            ingredient_key = matched_item.get("matched_ingredient_key")
            if ingredient_key and ingredient_key in self.ingredient_dict:
                ingredient_data = self.ingredient_dict[ingredient_key]
                source_urls = ingredient_data.get("sources", source_urls)
            
            return {
                "raw_name": raw_name,
                "found": True,
                "source": "drug_items",
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
