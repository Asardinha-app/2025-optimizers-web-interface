#!/usr/bin/env python3

import pandas as pd
import os
import sys
from typing import Optional, Dict, Any

# Add project root to sys.path for robust imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from mlb_optimizer_automation.daily_config import SABERSIM_CSV_PATH

class SaberSimProjectionScraper:
    """
    Scraper for SaberSim projections from CSV file.
    
    This scraper loads projections from a CSV file that contains:
    - DFS ID: Player identifier
    - Order: Roster Order for batters
    - fd_25_percentile: Projection floor
    - fd_85_percentile: Projection ceiling
    """
    
    def __init__(self, csv_path: str = None):
        self.csv_path = csv_path or SABERSIM_CSV_PATH
        self.source_name = "SaberSim"
        
    def run(self, output_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load and process SaberSim projections from CSV.
        
        Args:
            output_path: Optional path to save processed CSV
            
        Returns:
            DataFrame with processed projections
        """
        print(f"Starting {self.source_name} projection scrape")
        
        try:
            # Load CSV file
            if not os.path.exists(self.csv_path):
                print(f"❌ Error: CSV file not found at {self.csv_path}")
                return pd.DataFrame()
            
            print(f"Loading projections from: {self.csv_path}")
            df = pd.read_csv(self.csv_path)
            
            print(f"Loaded {len(df)} projections from {self.source_name}")
            
            # Process the data
            processed_df = self._process_projections(df)
            
            if processed_df.empty:
                print(f"❌ No valid projections found in {self.source_name}")
                return pd.DataFrame()
            
            # Save to file if requested
            if output_path:
                processed_df.to_csv(output_path, index=False)
                print(f"✅ Saved {self.source_name} projections to {output_path}")
            else:
                print(f"✅ Successfully scraped {self.source_name} projections (no file saved)")
            
            return processed_df
            
        except Exception as e:
            print(f"❌ Error scraping {self.source_name} projections: {e}")
            return pd.DataFrame()
    
    def _process_projections(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process raw CSV data into standardized projection format.
        
        Args:
            df: Raw CSV DataFrame
            
        Returns:
            Processed DataFrame with standardized columns
        """
        print(f"Processing {self.source_name} projections...")
        
        # Required columns
        required_cols = ['DFS ID', 'Name', 'Pos', 'Order', 'Team', 'Opp', 'fd_points', 'fd_25_percentile', 'fd_85_percentile']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"❌ Missing required columns: {missing_cols}")
            return pd.DataFrame()
        
        # Create processed DataFrame
        processed_data = []
        
        for _, row in df.iterrows():
            try:
                # Extract basic info
                dfs_id = str(row['DFS ID']).strip()
                name = str(row['Name']).strip()
                position = str(row['Pos']).strip()
                team = str(row['Team']).strip()
                opponent = str(row['Opp']).strip()
                
                # Extract roster order (for batters only)
                roster_order = row.get('Order', 0)
                if pd.isna(roster_order) or roster_order == '':
                    roster_order = 0
                else:
                    roster_order = int(roster_order)
                
                # Extract projections - use fd_points as primary projection
                fd_points = row.get('fd_points', 0)
                floor_proj = row.get('fd_25_percentile', 0)
                ceiling_proj = row.get('fd_85_percentile', 0)
                hits_proj = row.get('H', 0)  # Extract hits projection
                
                # Use fd_points as the main projection
                if pd.notna(fd_points) and float(fd_points) > 0:
                    main_projection = float(fd_points)
                else:
                    main_projection = 0
                
                # Only include players with valid projections
                if main_projection > 0:
                    processed_data.append({
                        'DFS ID': dfs_id,
                        'player_name': name,
                        'position': position,
                        'team': team,
                        'opponent': opponent,
                        'roster_order': roster_order,
                        'floor_projection': float(floor_proj) if pd.notna(floor_proj) else 0,
                        'ceiling_projection': float(ceiling_proj) if pd.notna(ceiling_proj) else 0,
                        'sabersim_projection': main_projection,
                        'hits_projection': float(hits_proj) if pd.notna(hits_proj) else 0
                    })
            
            except Exception as e:
                print(f"Warning: Error processing row for {row.get('Name', 'Unknown')}: {e}")
                continue
        
        if not processed_data:
            print("❌ No valid projections found after processing")
            return pd.DataFrame()
        
        # Create DataFrame
        result_df = pd.DataFrame(processed_data)
        
        # Print summary
        print(f"Processed {len(result_df)} valid projections from {self.source_name}")
        
        # Calculate projection statistics
        if 'sabersim_projection' in result_df.columns:
            projections = result_df['sabersim_projection']
            print(f"\n{self.source_name} Projection Summary:")
            print(f"Total projections: {len(projections)}")
            print(f"Average projection: {projections.mean():.2f}")
            print(f"Projection range: {projections.min():.2f} - {projections.max():.2f}")
            
            # Show sample data
            print(f"\nSample {self.source_name} projections:")
            sample_cols = ['DFS ID', 'player_name', 'position', 'team', 'roster_order', 'floor_projection', 'ceiling_projection', 'sabersim_projection']
            available_cols = [col for col in sample_cols if col in result_df.columns]
            print(result_df[available_cols].head())
        
        return result_df

def main():
    """Main function for testing the scraper."""
    scraper = SaberSimProjectionScraper()
    result = scraper.run()
    
    if not result.empty:
        print(f"\n✅ {len(result)} {scraper.source_name} projections loaded successfully")
    else:
        print(f"\n❌ Failed to load {scraper.source_name} projections")

if __name__ == "__main__":
    main() 