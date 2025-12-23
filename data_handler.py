"""
Data handling and export functionality
"""
import json
import csv
import os
import re
from typing import List, Dict
from datetime import datetime
import pandas as pd
from config import get_config


class DataHandler:
    """Handle data storage and export"""
    
    def __init__(self):
        self.config = get_config()
        self.output_dir = self.config["output"]["dir"]
        self.data_file = self.config["output"]["data_file"]
        self.csv_file = self.config["output"]["csv_file"]
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """Create output directory if it doesn't exist"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def save_json(self, data: List[Dict], filename: str = None) -> str:
        """
        Save data to JSON file
        
        Args:
            data: List of dictionaries to save
            filename: Optional custom filename
        
        Returns:
            Path to saved file
        """
        filename = filename or self.data_file
        
        # Add metadata
        output_data = {
            "metadata": {
                "scraped_at": datetime.now().isoformat(),
                "total_items": len(data),
            },
            "data": data,
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Data saved to {filename}")
        return filename
    
    def save_csv(self, data: List[Dict], filename: str = None) -> str:
        """
        Save data to CSV file
        
        Args:
            data: List of dictionaries to save
            filename: Optional custom filename
        
        Returns:
            Path to saved file
        """
        if not data:
            print("No data to save")
            return ""
        
        filename = filename or self.csv_file
        
        # Flatten nested dictionaries
        flattened_data = []
        for item in data:
            flattened_item = self._flatten_dict(item)
            flattened_data.append(flattened_item)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(flattened_data)
        df.to_csv(filename, index=False, encoding="utf-8")
        
        print(f"Data saved to {filename}")
        return filename
    
    def _flatten_dict(self, d: Dict, parent_key: str = "", sep: str = "_") -> Dict:
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert list to string representation
                items.append((new_key, json.dumps(v) if v else ""))
            else:
                items.append((new_key, v))
        return dict(items)
    
    def load_json(self, filename: str = None) -> List[Dict]:
        """
        Load data from JSON file
        
        Args:
            filename: Optional custom filename
        
        Returns:
            List of dictionaries
        """
        filename = filename or self.data_file
        
        if not os.path.exists(filename):
            print(f"File not found: {filename}")
            return []
        
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Extract data from metadata wrapper if present
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        
        return data if isinstance(data, list) else []
    
    def append_data(self, new_data: List[Dict], filename: str = None) -> str:
        """
        Append new data to existing JSON file
        
        Args:
            new_data: New data to append
            filename: Optional custom filename
        
        Returns:
            Path to saved file
        """
        filename = filename or self.data_file
        
        # Load existing data
        existing_data = self.load_json(filename)
        
        # Combine data (avoid duplicates based on URL)
        existing_urls = {item.get("url") for item in existing_data if item.get("url")}
        for item in new_data:
            if item.get("url") not in existing_urls:
                existing_data.append(item)
                existing_urls.add(item.get("url"))
        
        # Save combined data
        return self.save_json(existing_data, filename)
    
    def export_to_excel(self, data: List[Dict], filename: str = None) -> str:
        """
        Export data to Excel file
        
        Args:
            data: List of dictionaries to export
            filename: Optional custom filename
        
        Returns:
            Path to saved file
        """
        if not data:
            print("No data to export")
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/gumtree_data_{timestamp}.xlsx"
        
        # Flatten nested dictionaries
        flattened_data = []
        for item in data:
            flattened_item = self._flatten_dict(item)
            flattened_data.append(flattened_item)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(flattened_data)
        df.to_excel(filename, index=False, engine="openpyxl")
        
        print(f"Data exported to {filename}")
        return filename
    
    def get_statistics(self, data: List[Dict]) -> Dict:
        """
        Get statistics about the scraped data
        
        Args:
            data: List of dictionaries
        
        Returns:
            Dictionary with statistics
        """
        if not data:
            return {"total_items": 0}
        
        stats = {
            "total_items": len(data),
            "items_with_price": sum(1 for item in data if item.get("price")),
            "items_with_location": sum(1 for item in data if item.get("location")),
            "items_with_images": sum(1 for item in data if item.get("images")),
        }
        
        # Price statistics
        prices = []
        for item in data:
            price = item.get("price", "")
            if price:
                # Extract numeric value
                price_match = re.search(r"[\d,]+", str(price).replace(",", ""))
                if price_match:
                    try:
                        prices.append(float(price_match.group()))
                    except ValueError:
                        pass
        
        if prices:
            stats["price_stats"] = {
                "min": min(prices),
                "max": max(prices),
                "average": sum(prices) / len(prices),
            }
        
        return stats
