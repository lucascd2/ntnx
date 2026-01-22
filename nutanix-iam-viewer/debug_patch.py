#!/usr/bin/env python3
import re

# Read the original file
with open('prism_iam_roles_debug.py', 'r') as f:
    content = f.read()

# Replace the get_operation_details method with a debug version
old_method = '''    def get_operation_details(self, operations_cache, operation_ids):
        """Get details for specific operations"""
        if not operations_cache:
            print("Loading operations cache...")
            ops_response = self.list_operations(limit=1000)
            if not ops_response or 'data' not in ops_response:
                return {}
            
            for op in ops_response['data']:
                operations_cache[op['extId']] = op
        
        return {op_id: operations_cache.get(op_id, {'displayName': 'Unknown Operation', 'description': 'Operation not found'}) 
                for op_id in operation_ids}'''

new_method = '''    def get_operation_details(self, operations_cache, operation_ids):
        """Get details for specific operations"""
        if not operations_cache:
            print("Loading operations cache...")
            ops_response = self.list_operations(limit=1000)
            if not ops_response or 'data' not in ops_response:
                print("ERROR: No operations data received!")
                return {}
            
            print(f"DEBUG: Loaded {len(ops_response['data'])} operations from API")
            for op in ops_response['data']:
                operations_cache[op['extId']] = op
            print(f"DEBUG: Operations cache now has {len(operations_cache)} entries")
            
            # Print first few operations for debugging
            if operations_cache:
                print("DEBUG: Sample operations in cache:")
                for i, (ext_id, op) in enumerate(list(operations_cache.items())[:3]):
                    print(f"  {ext_id}: {op.get('displayName', 'N/A')}")
        
        print(f"DEBUG: Looking up {len(operation_ids)} operation IDs:")
        for op_id in operation_ids[:5]:  # Show first 5
            print(f"  {op_id}: {'FOUND' if op_id in operations_cache else 'NOT FOUND'}")
        
        result = {}
        for op_id in operation_ids:
            if op_id in operations_cache:
                result[op_id] = operations_cache[op_id]
            else:
                result[op_id] = {'displayName': 'Unknown Operation', 'description': 'Operation not found'}
        
        return result'''

# Replace the method
content = content.replace(old_method, new_method)

# Write the updated file
with open('prism_iam_roles_debug.py', 'w') as f:
    f.write(content)

print("Debug version created successfully!")
