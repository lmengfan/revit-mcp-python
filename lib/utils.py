# -*- coding: utf-8 -*-
from pyrevit import DB
import traceback
import logging

logger = logging.getLogger(__name__)


"""
Room Warning Swallower - Python Implementation
Translates C# IFailuresPreprocessor to suppress Revit room warnings
"""

import clr
from Autodesk.Revit.DB import (
    IFailuresPreprocessor, 
    FailureProcessingResult, 
    BuiltInFailures
)

class RoomWarningSwallower(IFailuresPreprocessor):
    """
    Failure preprocessor that suppresses specific room warnings in Revit.
    
    This class implements IFailuresPreprocessor to automatically dismiss
    "Room Not Enclosed" warnings during Revit operations.
    
    Usage:
        # Create and register the failure preprocessor
        swallower = RoomWarningSwallower()
        
        # Use during transaction
        transaction.Start()
        doc.Application.RegisterFailuresProcessor(swallower)
        # ... perform operations that might generate room warnings ...
        doc.Application.UnregisterFailuresProcessor(swallower)
        transaction.Commit()
    """
    
    def PreprocessFailures(self, failures_accessor):
        """
        Preprocesses failures to suppress specific room warnings.
        
        Args:
            failures_accessor: FailuresAccessor object containing failure messages
            
        Returns:
            FailureProcessingResult.Continue to continue processing
        """
        try:
            # Get all failure messages
            fail_list = failures_accessor.GetFailureMessages()
            
            # Process each failure message
            for failure in fail_list:
                # Get the failure definition ID
                fail_id = failure.GetFailureDefinitionId()
                
                # Check if this is a "Room Not Enclosed" warning and suppress it
                if fail_id == BuiltInFailures.RoomFailures.RoomNotEnclosed:
                    failures_accessor.DeleteWarning(failure)
            
            # Continue with normal processing
            return FailureProcessingResult.Continue
            
        except Exception as e:
            # Log error but continue processing to avoid breaking the workflow
            print("Error in RoomWarningSwallower: {}".format(str(e)))
            return FailureProcessingResult.Continue


class ExtendedRoomWarningSwallower(IFailuresPreprocessor):
    """
    Extended version that can suppress multiple types of room warnings.
    
    Usage:
        # Suppress multiple warning types
        swallower = ExtendedRoomWarningSwallower([
            BuiltInFailures.RoomFailures.RoomNotEnclosed,
            BuiltInFailures.RoomFailures.RoomNotInPhase,
            # Add other warning types as needed
        ])
    """
    
    def __init__(self, warning_types_to_suppress=None):
        """
        Initialize with specific warning types to suppress.
        
        Args:
            warning_types_to_suppress: List of FailureDefinitionId objects to suppress.
                                     If None, defaults to RoomNotEnclosed only.
        """
        if warning_types_to_suppress is None:
            self.warning_types = [BuiltInFailures.RoomFailures.RoomNotEnclosed]
        else:
            self.warning_types = warning_types_to_suppress
    
    def PreprocessFailures(self, failures_accessor):
        """
        Preprocesses failures to suppress configured room warnings.
        
        Args:
            failures_accessor: FailuresAccessor object containing failure messages
            
        Returns:
            FailureProcessingResult.Continue to continue processing
        """
        try:
            # Get all failure messages
            fail_list = failures_accessor.GetFailureMessages()
            suppressed_count = 0
            
            # Process each failure message
            for failure in fail_list:
                # Get the failure definition ID
                fail_id = failure.GetFailureDefinitionId()
                
                # Check if this failure type should be suppressed
                if fail_id in self.warning_types:
                    failures_accessor.DeleteWarning(failure)
                    suppressed_count += 1
            
            # Optional: Log suppressed warnings count
            if suppressed_count > 0:
                print("RoomWarningSwallower: Suppressed {} room warnings".format(suppressed_count))
            
            # Continue with normal processing
            return FailureProcessingResult.Continue
            
        except Exception as e:
            # Log error but continue processing to avoid breaking the workflow
            print("Error in ExtendedRoomWarningSwallower: {}".format(str(e)))
            return FailureProcessingResult.Continue


# Utility functions for easier usage
def create_room_warning_swallower():
    """
    Factory function to create a basic room warning swallower.
    
    Returns:
        RoomWarningSwallower instance
    """
    return RoomWarningSwallower()


def create_extended_room_warning_swallower(warning_types=None):
    """
    Factory function to create an extended room warning swallower.
    
    Args:
        warning_types: List of warning types to suppress
        
    Returns:
        ExtendedRoomWarningSwallower instance
    """
    return ExtendedRoomWarningSwallower(warning_types)


def suppress_room_warnings_during_transaction(doc, transaction, operation_func):
    """
    Context manager-like function to suppress room warnings during a transaction.
    
    Args:
        doc: Revit Document
        transaction: Transaction object
        operation_func: Function to execute with warning suppression
        
    Usage:
        def my_room_operation():
            # Operations that might generate room warnings
            pass
            
        suppress_room_warnings_during_transaction(doc, transaction, my_room_operation)
    """
    swallower = create_room_warning_swallower()
    
    try:
        # Register the failure processor
        doc.Application.RegisterFailuresProcessor(swallower)
        
        # Execute the operation
        operation_func()
        
    finally:
        # Always unregister the processor
        try:
            doc.Application.UnregisterFailuresProcessor(swallower)
        except:
            pass  # Ignore errors during cleanup


    # Example usage in pyRevit script
    """
    Example usage in a pyRevit script:

    from lib.RoomWarningSwallower import RoomWarningSwallower, suppress_room_warnings_during_transaction

    # Method 1: Manual registration
    swallower = RoomWarningSwallower()
    transaction.Start()
    doc.Application.RegisterFailuresProcessor(swallower)
    # ... perform room operations ...
    doc.Application.UnregisterFailuresProcessor(swallower)
    transaction.Commit()

    # Method 2: Using utility function
    def my_room_operations():
        # Room creation/modification code here
        pass

    transaction.Start()
    suppress_room_warnings_during_transaction(doc, transaction, my_room_operations)
    transaction.Commit()
    """ 

def normalize_string(text):
    """Safely normalize string values"""
    if text is None:
        return "Unnamed"
    return str(text).strip()


def get_element_name(element):
    """
    Get the name of a Revit element.
    Useful for both FamilySymbol and other elements.
    """
    try:
        return element.Name
    except AttributeError:
        return DB.Element.Name.__get__(element)


def find_family_symbol_safely(doc, target_family_name, target_type_name=None):
    """
    Safely find a family symbol by name
    """
    try:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)

        for symbol in collector:
            if symbol.Family.Name == target_family_name:
                if not target_type_name or symbol.Name == target_type_name:
                    return symbol
        return None
    except Exception as e:
        logger.error("Error finding family symbol: %s", str(e))
        return None


def find_element_by_source_id(doc, category, source_id):
    """
    Find a Revit element by searching for a matching Source_Id parameter value.
    
    Args:
        doc: Revit Document object
        category: BuiltInCategory enum value (e.g., DB.BuiltInCategory.OST_Walls)
        source_id: String ID to match against the Source_Id parameter
        
    Returns:
        ElementId: The element ID of the first matching element, or None if not found
        
    Example:
        # Find a wall with specific Source_Id
        wall_id = find_element_by_source_id(doc, DB.BuiltInCategory.OST_Walls, "WALL_001")
        if wall_id:
            wall_element = doc.GetElement(wall_id)
    """
    try:
        # Create collector for the specified category
        collector = DB.FilteredElementCollector(doc).OfCategory(category).WhereElementIsNotElementType()
        
        # Iterate through elements in the category
        for element in collector:
            try:
                # Try to get the Source_Id parameter
                source_id_param = element.LookupParameter("Source_Id")
                
                if source_id_param is not None and source_id_param.HasValue:
                    # Get parameter value as string
                    param_value = source_id_param.AsString()
                    
                    # Compare with target source_id (case-sensitive)
                    if param_value == source_id:
                        logger.info("Found element with Source_Id '%s': ElementId %s", source_id, element.Id)
                        return element.Id
                        
            except Exception as elem_error:
                # Log error for individual element but continue searching
                logger.debug("Error checking Source_Id for element %s: %s", element.Id, str(elem_error))
                continue
        
        # No matching element found
        logger.info("No element found with Source_Id: %s in category %s", source_id, category)
        return None
        
    except Exception as e:
        logger.error("Error searching for element with Source_Id '%s': %s", source_id, str(e))
        return None


def find_elements_by_source_id(doc, category, source_id):
    """
    Find all Revit elements by searching for matching Source_Id parameter values.
    
    Args:
        doc: Revit Document object
        category: BuiltInCategory enum value (e.g., DB.BuiltInCategory.OST_Walls)
        source_id: String ID to match against the Source_Id parameter
        
    Returns:
        List[ElementId]: List of element IDs for all matching elements, empty list if none found
        
    Example:
        # Find all walls with specific Source_Id
        wall_ids = find_elements_by_source_id(doc, DB.BuiltInCategory.OST_Walls, "WALL_001")
        for wall_id in wall_ids:
            wall_element = doc.GetElement(wall_id)
    """
    try:
        matching_elements = []
        
        # Create collector for the specified category
        collector = DB.FilteredElementCollector(doc).OfCategory(category).WhereElementIsNotElementType()
        
        # Iterate through elements in the category
        for element in collector:
            try:
                # Try to get the Source_Id parameter
                source_id_param = element.LookupParameter("Source_Id")
                
                if source_id_param is not None and source_id_param.HasValue:
                    # Get parameter value as string
                    param_value = source_id_param.AsString()
                    
                    # Compare with target source_id (case-sensitive)
                    if param_value == source_id:
                        matching_elements.append(element.Id)
                        
            except Exception as elem_error:
                # Log error for individual element but continue searching
                logger.debug("Error checking Source_Id for element %s: %s", element.Id, str(elem_error))
                continue
        
        logger.info("Found %d elements with Source_Id '%s' in category %s", 
                   len(matching_elements), source_id, category)
        return matching_elements
        
    except Exception as e:
        logger.error("Error searching for elements with Source_Id '%s': %s", source_id, str(e))
        return []
