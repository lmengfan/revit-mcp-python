#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ATF Component Models

Contains classes and functions for deserializing ATF component JSON responses
from model.QueryObject() into structured Python objects.
"""

import json


class ComponentChild(object):
    """Represents a child component in the ATF component structure"""
    
    def __init__(self, id=None):
        self.id = id
    
    @classmethod
    def from_dict(cls, data):
        """Create ComponentChild from dictionary"""
        if not data:
            return None
        return cls(id=data.get("id"))
    
    def to_dict(self):
        """Convert ComponentChild to dictionary"""
        return {"id": self.id}
    
    def __str__(self):
        return "ComponentChild(id={})".format(self.id)


class PropertyParameter(object):
    """Represents an ATF PropertyParameter object"""
    
    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value
    
    @classmethod
    def from_dict(cls, data):
        """Create PropertyParameter from dictionary"""
        if not data:
            return None

        key, value = data.keys()[0], data.values()[0]
        return cls(name=key, value=value)

    def to_dict(self):
        """Convert PropertyParameter to dictionary"""
        return {"name": self.name, "value": self.value}
    
    def __str__(self):
        return "PropertyParameter(name={}, value={})".format(self.name, self.value)


class PropertySet(object):
    """Represents an ATF PropertySet object"""
    
    def __init__(self, name=None, label=None, description=None, parameters=None):
        self.name = name
        self.label = label
        self.description = description
        self.parameters = parameters or []
    
    @classmethod
    def from_dict(cls, data):
        """Create PropertySet from dictionary"""
        if not data:
            return None
        
        parameters = []
        if "properties" in data and data["properties"]:
            for param_data in data["properties"]:
                param = PropertyParameter.from_dict(param_data)
                if param:
                    parameters.append(param)

        return cls(name=data.get("name"), label=data.get("label"), description=data.get("description"), parameters=parameters)

    def get_parameters(self):
        """Get all parameters"""
        return self.parameters
    
    def to_dict(self):
        """Convert PropertySet to dictionary"""
        return {"name": self.name, "label": self.label, "description": self.description, "parameters": [param.to_dict() for param in self.parameters]}
    
    def __str__(self):
        return "PropertySet(name={}, label={}, description={}, parameters={})".format(self.name, self.label, self.description, self.parameters)


class ComponentInstance(object):
    """Represents an ATF ComponentInstance object"""
    
    def __init__(self, id=None, label=None, type=None, component_definition_id=None, property_sets=None):
        self.id = id
        self.label = label
        self.type = type
        self.component_definition_id = component_definition_id
        self.property_sets = property_sets or []
    
    @classmethod
    def from_dict(cls, data):
        """Create ComponentInstance from dictionary"""
        if not data:
            return None
         # Parse children
        property_sets = []
        if "properties" in data and data["properties"]:
            for prop_data in data["properties"]:
                if "type" in prop_data and prop_data["type"] == "PropertySet":
                    propSet = PropertySet.from_dict(prop_data)
                    if propSet:
                        property_sets.append(propSet)

        return cls(
            id=data.get("id"),
            label=data.get("label"),
            type=data.get("type"),
            component_definition_id=data.get("componentDefinitionId"),
            property_sets=property_sets
        )

    def get_property_sets(self):
        """Get all property sets"""
        return self.property_sets
    
    def to_dict(self):
        """Convert ComponentInstance to dictionary"""
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "componentDefinitionId": self.component_definition_id,
            "properties": [propSet.to_dict() for propSet in self.property_sets]
        }
    
    def __str__(self):
        return "ComponentInstance(id={}, label={}, componentDefinitionId={}, properties={})".format(
            self.id, self.label, self.component_definition_id, self.property_sets
        )

class ComponentDefinition(object):
    """Represents an ATF ComponentDefinition object"""
    
    def __init__(self, id=None, label=None, type=None, children=None):
        self.id = id
        self.label = label
        self.type = type
        self.children = children or []
    
    @classmethod
    def from_dict(cls, data):
        """Create ComponentDefinition from dictionary"""
        if not data:
            return None
        
        # Parse children
        children = []
        if "children" in data and data["children"]:
            for child_data in data["children"]:
                child = ComponentChild.from_dict(child_data)
                if child:
                    children.append(child)
        
        return cls(
            id=data.get("id"),
            label=data.get("label"),
            type=data.get("type"),
            children=children
        )
    
    def to_dict(self):
        """Convert ComponentDefinition to dictionary"""
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "children": [child.to_dict() for child in self.children]
        }
    
    def get_child_count(self):
        """Get count of children"""
        return len(self.children)

    def get_child_ids(self):
        """Get list of all child IDs"""
        return [child.id for child in self.children if child.id]

    def __str__(self):
        return "ComponentDefinition(id={}, label={}, type={}, children_count={})".format(
            self.id, self.label, self.type, len(self.children))



def deserialize_component_dict(data_dict):
    """
    Deserialize dictionary from model.QueryObject() into ComponentDefinition object
    
    Args:
        data_dict (dict): Dictionary from ATF model.QueryObject()
        
    Returns:
        ComponentDefinition: Parsed component definition object, or None if parsing fails
    """
    try:
        if not data_dict:
            print("[ERROR] Empty dictionary provided")
            return None
        
        # Create ComponentDefinition object
        component = ComponentDefinition.from_dict(data_dict)
        
        return component
        
    except Exception as e:
        print("[ERROR] Failed to deserialize component: {}".format(e))
        return None


def deserialize_component_auto(component_data):
    """
    Automatically deserialize component data (string or dict) into ComponentDefinition or ComponentInstance object
    
    Args:
        component_data: JSON string or dictionary from ATF model.QueryObject()
        
    Returns:
        ComponentDefinition or ComponentInstance: Parsed component object, or None if parsing fails
    """
    try:
        if not component_data:
            print("[ERROR] No component data provided")
            return None
        
        parsed_data = None
        
        # Parse data if it's a string
        if isinstance(component_data, str):
            parsed_data = json.loads(component_data)
        else:
            parsed_data = component_data
        
        # Determine component type and deserialize accordingly
        component_type = parsed_data.get("type", "")
        
        if component_type == "ComponentDefinition":
            return deserialize_component_dict(parsed_data)
        elif component_type == "ComponentInstance":
            return ComponentInstance.from_dict(parsed_data)
        else:
            print("[WARNING] Unknown component type '{}', attempting ComponentDefinition deserialization".format(component_type))
            return deserialize_component_dict(parsed_data)
            
    except Exception as e:
        print("[ERROR] Failed to auto-deserialize component: {}".format(e))
        return None


def traverse_component_hierarchy(model, componentObject, visited_ids=None, depth=0, max_depth=10):
    """
    Recursively traverse all children of a component using model.QueryObject()
    
    This is a simple placeholder function for future work that will process
    the entire component hierarchy starting from a root component.
    
    Args:
        model: ATF InteropModel instance with QueryObject method
        componentObject: component object to start traversal from
        visited_ids (set, optional): Set of already visited component IDs (for cycle detection)
        depth (int, optional): Current traversal depth (default: 0)
        max_depth (int, optional): Maximum traversal depth to prevent infinite recursion (default: 10)
    
    Returns:
        dict: Traversal results with component data and children
        
    Example:
        results = traverse_component_hierarchy(model, componentObject)
        print("Total components found:", len(results.get("all_components", [])))
    """
    try:
        # Initialize visited_ids set for cycle detection
        if visited_ids is None:
            visited_ids = set()
        
        # Check for maximum depth to prevent infinite recursion
        if depth > max_depth:
            print("[WARNING] Maximum traversal depth ({}) reached for component: {}".format(max_depth, componentObject.Id))
            return {"component": None, "children": [], "error": "Max depth reached"}
        
        # Check if we've already visited this component (cycle detection)
        if componentObject.Id in visited_ids:
            print("[WARNING] Cycle detected - component {} already visited".format(componentObject.Id))
            return {"component": None, "children": [], "error": "Cycle detected"}
        
        # Add current component to visited set
        visited_ids.add(componentObject.Id)
        
        # Query the component using the model
        # pass a properly formatted JSON string with options
        options = {"optional": ["property"]}
        component_json = model.QueryObject(componentObject, json.dumps(options))
        if not component_json:
            print("{}[WARNING] No data returned for component: {}".format("  " * depth, componentObject.Id))
            return {"component": None, "children": [], "error": "No data returned"}
        
        # Deserialize the component
        component = deserialize_component_auto(component_json)
        if not component:
            print("{}[ERROR] Failed to deserialize component: {}".format("  " * depth, componentObject.Id))
            return {"component": None, "children": [], "error": "Deserialization failed"}

        # Recursively process based on component type
        children_results = []
        if isinstance(component, ComponentDefinition):
            # For ComponentDefinition: traverse children directly
            child_count = component.get_child_count()
            
            for componentChild in component.children:
                if componentChild.id:
                    childObject = model.GetObject(componentChild.id)
                    child_result = traverse_component_hierarchy(model, childObject, visited_ids, depth + 1, max_depth)
                    children_results.append(child_result)
                    
        elif isinstance(component, ComponentInstance):
            # For ComponentInstance: traverse the componentDefinitionId
            if component.component_definition_id:
                definitionObject = model.GetObject(component.component_definition_id)
                definition_result = traverse_component_hierarchy(model, definitionObject, visited_ids, depth + 1, max_depth)
                children_results.append(definition_result)
            else:
                print("{}[WARNING] ComponentInstance has no componentDefinitionId".format("  " * depth))
        else:
            print("{}[WARNING] Unknown component type: {}".format("  " * depth, type(componentObject)))
        
        # Return results
        result = {
            "component": component,
            "children": children_results,
            "depth": depth,
            "component_id": component.id,
            "error": None
        }
        
        return result
        
    except Exception as e:
        print("{}[ERROR] Failed to traverse component {}: {}".format("  " * depth, componentObject.Id(), str(e)))
        return {
            "component": None, 
            "children": [], 
            "error": str(e),
            "depth": depth,
            "component_id": componentObject.Id()
        }


def _count_total_components(traversal_result):
    """
    Helper function to count total components in a traversal result with separate counts
    
    Args:
        traversal_result (dict): Result from traverse_component_hierarchy
        
    Returns:
        dict: Component counts {"total": int, "definitions": int, "instances": int}
    """
    try:
        counts = {"total": 0, "definitions": 0, "instances": 0}
        
        # Count current component if it exists
        component = traversal_result.get("component")
        if component:
            counts["total"] += 1
            if isinstance(component, ComponentDefinition):
                counts["definitions"] += 1
            elif isinstance(component, ComponentInstance):
                counts["instances"] += 1
        
        # Recursively count children
        for child_result in traversal_result.get("children", []):
            child_counts = _count_total_components(child_result)
            counts["total"] += child_counts["total"]
            counts["definitions"] += child_counts["definitions"]
            counts["instances"] += child_counts["instances"]
        
        return counts
        
    except Exception as e:
        print("[ERROR] Failed to count components: {}".format(str(e)))
        return {"total": 0, "definitions": 0, "instances": 0}


def get_all_component_ids(traversal_result):
    """
    Extract all component IDs from a traversal result
    
    Args:
        traversal_result (dict): Result from traverse_component_hierarchy
        
    Returns:
        list: List of all component IDs found during traversal
    """
    try:
        component_ids = []
        
        # Add current component ID if it exists
        component = traversal_result.get("component")
        if component:
            component_ids.append(component.id)
        
        # Recursively collect children IDs
        for child_result in traversal_result.get("children", []):
            component_ids.extend(get_all_component_ids(child_result))
        
        return component_ids
        
    except Exception as e:
        print("[ERROR] Failed to extract component IDs: {}".format(str(e)))
        return []

def get_component_ids_by_type(traversal_result):
    """
    Extract component IDs from a traversal result grouped by type
    
    Args:
        traversal_result (dict): Result from traverse_component_hierarchy
        
    Returns:
        dict: Component IDs grouped by type {"definitions": [], "instances": [], "all": []}
    """
    try:
        component_ids = {"definitions": [], "instances": [], "all": []}
        
        # Add current component ID if it exists
        component = traversal_result.get("component")
        if component:
            component_ids["all"].append(component)
            if isinstance(component, ComponentDefinition):
                component_ids["definitions"].append(component)
            elif isinstance(component, ComponentInstance):
                component_ids["instances"].append(component)
        
        # Recursively collect children IDs
        for child_result in traversal_result.get("children", []):
            child_ids = get_component_ids_by_type(child_result)
            component_ids["all"].extend(child_ids["all"])
            component_ids["definitions"].extend(child_ids["definitions"])
            component_ids["instances"].extend(child_ids["instances"])
        
        return component_ids
        
    except Exception as e:
        print("[ERROR] Failed to extract component IDs by type: {}".format(str(e)))
        return {"definitions": [], "instances": [], "all": []}


