"""
Test suite for CSV Handler

This module tests the CSV handling functionality for the late swap optimizer.
"""

import unittest
import tempfile
import os
from pathlib import Path
import csv

# Import the functions to test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from data.processors.csv_handler import (
    load_template_lineups, 
    export_swapped_lineups, 
    validate_csv_format,
    create_sample_template
)

class TestCSVHandler(unittest.TestCase):
    """Test cases for CSV handler functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.sample_template_path = os.path.join(self.temp_dir, "sample_template.csv")
        
        # Create a sample template for testing
        create_sample_template(self.sample_template_path, num_lineups=3)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_create_sample_template(self):
        """Test creating a sample template"""
        # Test that the sample template was created
        self.assertTrue(os.path.exists(self.sample_template_path))
        
        # Test that the file has the expected content
        with open(self.sample_template_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            # Should have header + 3 lineups
            self.assertEqual(len(rows), 4)
            
            # Check header
            expected_header = ['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF', 'UTIL']
            self.assertEqual(rows[0], expected_header)
            
            # Check that each row has 9 player IDs
            for i in range(1, 4):
                self.assertEqual(len(rows[i]), 9)
                # Check that all values are numeric
                for value in rows[i]:
                    self.assertTrue(value.isdigit())
    
    def test_load_template_lineups(self):
        """Test loading lineups from template"""
        lineups = load_template_lineups(self.sample_template_path)
        
        # Should have 3 lineups
        self.assertEqual(len(lineups), 3)
        
        # Check that each lineup has the expected structure
        for lineup in lineups:
            self.assertIn('P', lineup)
            self.assertIn('C/1B', lineup)
            self.assertIn('2B', lineup)
            self.assertIn('3B', lineup)
            self.assertIn('SS', lineup)
            self.assertIn('OF', lineup)
            self.assertIn('UTIL', lineup)
            
            # Check that all values are present
            for key in ['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'UTIL']:
                self.assertIsNotNone(lineup[key])
                self.assertNotEqual(lineup[key], '')
    
    def test_validate_csv_format(self):
        """Test CSV format validation"""
        # Test valid format
        with open(self.sample_template_path, 'r') as f:
            reader = csv.DictReader(f)
            csv_data = list(reader)
        
        self.assertTrue(validate_csv_format(csv_data))
        
        # Test invalid format (missing columns)
        invalid_data = [{'P': '1001', 'C/1B': '2001'}]  # Missing required columns
        self.assertFalse(validate_csv_format(invalid_data))
        
        # Test empty data
        self.assertFalse(validate_csv_format([]))
    
    def test_export_swapped_lineups(self):
        """Test exporting swapped lineups"""
        # Create a mock lineup object
        class MockLineup:
            def __init__(self, players):
                self.players = players
        
        # Create mock lineup data
        mock_lineup = MockLineup([
            {
                "Slot": "P", "Id": 1001, "Name": "Pitcher 1", "Team": "TEAM1",
                "Salary": 9000, "Projection": 25.5, "Ownership": 0.15
            },
            {
                "Slot": "C/1B", "Id": 2001, "Name": "Catcher 1", "Team": "TEAM2",
                "Salary": 3500, "Projection": 12.3, "Ownership": 0.08
            },
            {
                "Slot": "2B", "Id": 3001, "Name": "Second Baseman 1", "Team": "TEAM3",
                "Salary": 3800, "Projection": 14.7, "Ownership": 0.12
            },
            {
                "Slot": "3B", "Id": 4001, "Name": "Third Baseman 1", "Team": "TEAM4",
                "Salary": 4200, "Projection": 16.2, "Ownership": 0.10
            },
            {
                "Slot": "SS", "Id": 5001, "Name": "Shortstop 1", "Team": "TEAM5",
                "Salary": 4100, "Projection": 15.8, "Ownership": 0.11
            },
            {
                "Slot": "OF", "Id": 6001, "Name": "Outfielder 1", "Team": "TEAM6",
                "Salary": 3900, "Projection": 13.5, "Ownership": 0.09
            },
            {
                "Slot": "OF", "Id": 6002, "Name": "Outfielder 2", "Team": "TEAM7",
                "Salary": 3700, "Projection": 12.8, "Ownership": 0.07
            },
            {
                "Slot": "OF", "Id": 6003, "Name": "Outfielder 3", "Team": "TEAM8",
                "Salary": 3600, "Projection": 12.1, "Ownership": 0.06
            },
            {
                "Slot": "UTIL", "Id": 7001, "Name": "Utility 1", "Team": "TEAM9",
                "Salary": 3400, "Projection": 11.9, "Ownership": 0.05
            }
        ])
        
        # Create mock LateSwapLineup objects
        class MockLateSwapLineup:
            def __init__(self, swapped_lineup):
                self.swapped_lineup = swapped_lineup
        
        mock_late_swap_lineups = [
            MockLateSwapLineup(mock_lineup),
            MockLateSwapLineup(mock_lineup)
        ]
        
        # Test export
        output_path = os.path.join(self.temp_dir, "test_export.csv")
        export_swapped_lineups(mock_late_swap_lineups, output_path)
        
        # Check that file was created
        self.assertTrue(os.path.exists(output_path))
        
        # Check file content
        with open(output_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            # Should have header + 2 lineups
            self.assertEqual(len(rows), 3)
            
            # Check header
            expected_header = ['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF', 'UTIL']
            self.assertEqual(rows[0], expected_header)
            
            # Check that each row has 9 player IDs
            for i in range(1, 3):
                self.assertEqual(len(rows[i]), 9)
    
    def test_file_not_found_error(self):
        """Test handling of file not found error"""
        non_existent_file = os.path.join(self.temp_dir, "non_existent.csv")
        
        with self.assertRaises(FileNotFoundError):
            load_template_lineups(non_existent_file)
    
    def test_invalid_csv_format(self):
        """Test handling of invalid CSV format"""
        # Create an invalid CSV file
        invalid_csv_path = os.path.join(self.temp_dir, "invalid.csv")
        with open(invalid_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Invalid', 'Columns'])
            writer.writerow(['Data1', 'Data2'])
        
        with self.assertRaises(ValueError):
            load_template_lineups(invalid_csv_path)

if __name__ == '__main__':
    unittest.main() 