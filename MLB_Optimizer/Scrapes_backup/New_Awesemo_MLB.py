import json
import pandas as pd
import requests
from datetime import datetime
import os
import sys

# Add project root to sys.path for robust imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from mlb_optimizer_automation.daily_config import AWESEMO_SLATE_ID

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

class AwesemoProjectionScraper:
    def __init__(self, slate_id=None):
        """
        Initialize the Awesemo projection scraper.
        
        Args:
            slate_id (int): The slate ID to scrape. If None, uses default from daily_config.
        """
        self.slate_id = slate_id or AWESEMO_SLATE_ID
        self.base_url = 'https://app-api-dfs-prod-main.azurewebsites.net/api/slatedata/projections'
        
    def get_projections(self):
        """Fetch projections from Awesemo API."""
        try:
            url = f'{self.base_url}?SlateId={self.slate_id}'
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = json.loads(response.text)
            df = pd.DataFrame(data)
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from Awesemo API: {e}")
            return pd.DataFrame()
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Unexpected error: {e}")
            return pd.DataFrame()
    
    def process_projections(self, df):
        """Process the raw projections into a standardized format."""
        if df.empty:
            return pd.DataFrame()
        
        try:
            # Extract DFS ID from nameAndId
            df['DFS ID'] = df['nameAndId'].str.split(':').str[0]
            
            # Convert ownership to percentage
            df['pOWN'] = df['ownership'] * 100
            
            # Select and rename columns for standardization
            processed_df = df[[
                'DFS ID', 'name', 'salary', 'lineupPosition', 
                'position', 'team', 'opponent', 'projection', 
                'pOWN', 'confirmedLineup'
            ]].copy()
            
            # Fill NaN values
            processed_df = processed_df.fillna(0)
            
            # Filter out projections below threshold
            processed_df = processed_df[processed_df['projection'] > 1]
            
            # Add source identifier
            processed_df['projection_source'] = 'Awesemo'
            
            # Rename columns to match our standard format
            processed_df = processed_df.rename(columns={
                'name': 'player_name',
                'projection': 'awesemo_projection',
                'pOWN': 'awesemo_ownership'
            })
            # Keep DFS ID as is for consistent matching
            
            print(f"Processed {len(processed_df)} valid projections")
            return processed_df
            
        except Exception as e:
            print(f"Error processing projections: {e}")
            return pd.DataFrame()
    
    def save_projections(self, df, output_path=None):
        """Save projections to CSV file."""
        if df.empty:
            print("No projections to save")
            return
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f'/Users/adamsardinha/Desktop/Awesemo_MLB_FD_{timestamp}.csv'
        
        try:
            df.to_csv(output_path, index=False)
            print(f"Projections saved to: {output_path}")
            return output_path
        except Exception as e:
            print(f"Error saving projections: {e}")
            return None
    
    def run(self, output_path=None):
        """Run the complete scraping process."""
        
        # Fetch projections
        raw_df = self.get_projections()
        if raw_df.empty:
            return None
        
        # Process projections
        processed_df = self.process_projections(raw_df)
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
    scraper = AwesemoProjectionScraper()
    output_path = scraper.run()
    
    if output_path:
        print(f"\n✅ Successfully scraped Awesemo projections")
        print(f"Output file: {output_path}")
    else:
        print("\n❌ Failed to scrape Awesemo projections")

if __name__ == "__main__":
    main()