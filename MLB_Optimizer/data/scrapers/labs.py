import requests
import pandas as pd
from datetime import datetime
import os
import sys

# Add project root to sys.path for robust imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config.scraper_config import LABS_SIMALBS_URL, LABS_PROJECTION_URL

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

class LabsProjectionScraper:
    def __init__(self, simalbs_url=None, proj_url=None):
        """
        Initialize Labs projection scraper.
        
        Args:
            simalbs_url: URL for SimLabs player data. If None, uses default from daily_config.
            proj_url: URL for FantasyLabs projections. If None, uses default from daily_config.
        """
        self.simalbs_url = simalbs_url or LABS_SIMALBS_URL
        self.proj_url = proj_url or LABS_PROJECTION_URL
        
    def fetch_json(self, url: str) -> list:
        """Fetches JSON data from the given URL and returns it as a Python list."""
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return []
    
    def load_player_data(self) -> pd.DataFrame:
        """Loads the SimLabs MLB JSON (player data) and returns a DataFrame."""
        data = self.fetch_json(self.simalbs_url)
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        return df
    
    def load_projection_data(self) -> pd.DataFrame:
        """Loads the FantasyLabs projection JSON and returns a DataFrame."""
        data = self.fetch_json(self.proj_url)
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        # Rename "id" → "FantasyResultId"
        df = df.rename(columns={"id": "FantasyResultId"})
        # Drop the nested "ownership" column (or keep it if you want to inspect ownership details)
        if "ownership" in df.columns:
            df = df.drop(columns=["ownership"])
        
        return df
    
    def merge_data(self, df_players: pd.DataFrame, df_proj: pd.DataFrame) -> pd.DataFrame:
        """Merge player data with projections."""
        if df_players.empty or df_proj.empty:
            return pd.DataFrame()
        
        # Merge on FantasyResultId
        merged = pd.merge(
            df_players,
            df_proj,
            on="FantasyResultId",
            how="inner",     # only rows present in both
            suffixes=("_player", "_proj")
        )
        
        return merged
    
    def process_projections(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process the merged data into a standardized format."""
        if df.empty:
            return pd.DataFrame()
        
        try:
            # Select and rename columns for standardization
            # We'll need to map the columns based on what's available
            processed_df = df.copy()
            
            # Add source identifier
            processed_df['projection_source'] = 'Labs'
            
            # Rename columns to match our standard format
            column_mapping = {
                'PlayerName': 'player_name',
                'Position': 'position',
                'Team': 'team',
                'FantasyResultId': 'DFS ID',
                'Projection': 'labs_projection'
            }
            
            # Apply column mapping for columns that exist
            for old_col, new_col in column_mapping.items():
                if old_col in processed_df.columns:
                    processed_df[new_col] = processed_df[old_col]
            
            # Ensure we have the required columns
            required_columns = ['player_name', 'position', 'team', 'labs_projection']
            missing_columns = [col for col in required_columns if col not in processed_df.columns]
            
            if missing_columns:
                return pd.DataFrame()
            
            # Filter out projections below threshold
            processed_df = processed_df[processed_df['labs_projection'] > 1]
            
            # No ownership processing needed - using Awesemo ownership as source of truth
            
            return processed_df
            
        except Exception as e:
            print(f"Error processing projections: {e}")
            return pd.DataFrame()
    
    def save_projections(self, df: pd.DataFrame, output_path=None):
        """Save projections to CSV file."""
        if df.empty:
            print("No projections to save")
            return
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f'/Users/adamsardinha/Desktop/Labs_MLB_FD_{timestamp}.csv'
        
        try:
            df.to_csv(output_path, index=False)
            print(f"Projections saved to: {output_path}")
            return output_path
        except Exception as e:
            print(f"Error saving projections: {e}")
            return None
    
    def run(self, output_path=None):
        """Run the complete scraping process."""
        
        # Load player data
        df_players = self.load_player_data()
        if df_players.empty:
            return None
        
        # Load projection data
        df_proj = self.load_projection_data()
        if df_proj.empty:
            return None
        
        # Merge data
        merged_df = self.merge_data(df_players, df_proj)
        if merged_df.empty:
            return None
        
        # Process projections
        processed_df = self.process_projections(merged_df)
        if processed_df.empty:
            return None
        
        # Optionally save to file if output_path is provided
        if output_path:
            saved_path = self.save_projections(processed_df, output_path)
            return saved_path
        else:
            return processed_df

def main():
    """Main function to run the scraper."""
    scraper = LabsProjectionScraper()
    result = scraper.run()
    
    if isinstance(result, str):
        print(f"\n✅ Successfully scraped Labs projections")
        print(f"Output file: {result}")
    elif isinstance(result, pd.DataFrame) and not result.empty:
        print(f"\n✅ Successfully scraped Labs projections")
        print(f"DataFrame returned with {len(result)} rows")
    else:
        print("\n❌ Failed to scrape Labs projections")

if __name__ == "__main__":
    main()
