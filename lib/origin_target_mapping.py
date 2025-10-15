"""
Origin-Target ID Mapping Utility

This module provides functionality to manage mappings between Origin GUIDs and Target IDs.
The mapping data is stored in a JSON file in the same directory as this script.
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, Any


class OriginTargetMappingManager:
    """Manages mappings between Origin GUIDs and Target IDs."""
    
    def __init__(self, filename: str = "origin_target_mapping.json"):
        """
        Initialize the mapping manager.
        
        Args:
            filename: Name of the JSON file to store mappings
        """
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.mapping_file = os.path.join(script_dir, filename)
        self._load_mappings()
    
    def _load_mappings(self) -> None:
        """Load mappings from JSON file or create empty structure."""
        try:
            if os.path.exists(self.mapping_file):
                with open(self.mapping_file, 'r') as f:
                    self.data = json.load(f)
            else:
                self._create_empty_mapping_file()
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading mapping file: {e}")
            self._create_empty_mapping_file()
    
    def _create_empty_mapping_file(self) -> None:
        """Create an empty mapping structure."""
        self.data = {
            "mappings": {},
            "metadata": {
                "version": "1.0",
                "created_date": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_mappings": 0
            }
        }
        self._save_mappings()
    
    def _save_mappings(self) -> None:
        """Save mappings to JSON file."""
        try:
            self.data["metadata"]["last_updated"] = datetime.now().isoformat()
            self.data["metadata"]["total_mappings"] = len(self.data["mappings"])
            
            with open(self.mapping_file, 'w') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving mapping file: {e}")
    
    def add_mapping(self, origin_guid: str, target_id: str, 
                   element_type: str = "", additional_data: Dict[str, Any] = None) -> bool:
        """
        Add or update a mapping between Origin GUID and Target ID.
        
        Args:
            origin_guid: Origin element GUID
            target_id: Target element ID
            element_type: Type of element (Beam, Column, etc.)
            additional_data: Additional metadata to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            mapping_entry = {
                "target_id": target_id,
                "element_type": element_type,
                "created_date": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            
            # Add any additional data
            if additional_data:
                mapping_entry.update(additional_data)
            
            # If mapping already exists, preserve creation date
            if origin_guid in self.data["mappings"]:
                mapping_entry["created_date"] = self.data["mappings"][origin_guid].get(
                    "created_date", mapping_entry["created_date"]
                )
            
            self.data["mappings"][origin_guid] = mapping_entry
            self._save_mappings()
            return True
        except Exception as e:
            print(f"Error adding mapping: {e}")
            return False
    
    def get_target_id(self, origin_guid: str) -> Optional[str]:
        """
        Get Target ID for a given Origin GUID.
        
        Args:
            origin_guid: Origin element GUID
            
        Returns:
            Target ID if found, None otherwise
        """
        mapping = self.data["mappings"].get(origin_guid)
        return mapping.get("target_id") if mapping else None
    
    def get_origin_guid(self, target_id: str) -> Optional[str]:
        """
        Get Origin GUID for a given Target ID.
        
        Args:
            target_id: Target element ID
            
        Returns:
            Origin GUID if found, None otherwise
        """
        for guid, mapping in self.data["mappings"].items():
            if mapping.get("target_id") == target_id:
                return guid
        return None
    
    def remove_mapping(self, origin_guid: str) -> bool:
        """
        Remove a mapping by Origin GUID.
        
        Args:
            origin_guid: Origin element GUID
            
        Returns:
            True if removed, False if not found
        """
        if origin_guid in self.data["mappings"]:
            del self.data["mappings"][origin_guid]
            self._save_mappings()
            return True
        return False
    
    def get_all_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get all mappings."""
        return self.data["mappings"].copy()
    
    def get_mapping_info(self, origin_guid: str) -> Optional[Dict[str, Any]]:
        """
        Get complete mapping information for an Origin GUID.
        
        Args:
            origin_guid: Origin element GUID
            
        Returns:
            Complete mapping data if found, None otherwise
        """
        return self.data["mappings"].get(origin_guid)
    
    def clear_all_mappings(self) -> None:
        """Clear all mappings."""
        self.data["mappings"] = {}
        self._save_mappings()
    
    def export_to_csv(self, csv_filename: str = None) -> str:
        """
        Export mappings to CSV file.
        
        Args:
            csv_filename: CSV filename (optional)
            
        Returns:
            Path to created CSV file
        """
        if not csv_filename:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            csv_filename = os.path.join(script_dir, "origin_target_mapping.csv")
        
        try:
            import csv
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['origin_guid', 'target_id', 'element_type', 'created_date', 'last_updated']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for guid, mapping in self.data["mappings"].items():
                    row = {
                        'origin_guid': guid,
                        'target_id': mapping.get('target_id', ''),
                        'element_type': mapping.get('element_type', ''),
                        'created_date': mapping.get('created_date', ''),
                        'last_updated': mapping.get('last_updated', '')
                    }
                    writer.writerow(row)
            
            return csv_filename
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return ""
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get mapping statistics."""
        mappings = self.data["mappings"]
        element_types = {}
        
        for mapping in mappings.values():
            elem_type = mapping.get("element_type", "Unknown")
            element_types[elem_type] = element_types.get(elem_type, 0) + 1
        
        return {
            "total_mappings": len(mappings),
            "element_types": element_types,
            "file_path": self.mapping_file,
            "last_updated": self.data["metadata"].get("last_updated", "Unknown")
        }


# Example usage functions for Origin system scripts
def get_mapping_manager() -> OriginTargetMappingManager:
    """Get a mapping manager instance."""
    return OriginTargetMappingManager()


def add_element_mapping(origin_element, target_id: str) -> bool:
    """
    Add mapping for an Origin element.
    
    Args:
        origin_element: Origin element object (e.g., Revit element)
        target_id: Target element ID (e.g., Tekla ID)
        
    Returns:
        True if successful
    """
    try:
        manager = get_mapping_manager()
        guid = origin_element.UniqueId
        element_type = origin_element.Category.Name if origin_element.Category else "Unknown"
        
        additional_data = {
            "origin_id": origin_element.Id.Value,
            "origin_category": element_type
        }
        
        return manager.add_mapping(guid, target_id, element_type, additional_data)
    except Exception as e:
        print(f"Error adding element mapping: {e}")
        return False


def get_target_id_for_element(origin_element) -> Optional[str]:
    """
    Get Target ID for an Origin element.
    
    Args:
        origin_element: Origin element object (e.g., Revit element)
        
    Returns:
        Target ID if found, None otherwise
    """
    try:
        manager = get_mapping_manager()
        return manager.get_target_id(origin_element.UniqueId)
    except Exception as e:
        print(f"Error getting Target ID: {e}")
        return None 