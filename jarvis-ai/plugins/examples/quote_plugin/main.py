"""
Quote Plugin - Inspirational quotes.

Demonstrates a simple JARVIS plugin.
"""

import random
from typing import Dict, List

# Import from parent
import sys
sys.path.insert(0, '../../../')

try:
    from plugins.loader import Plugin
except ImportError:
    class Plugin:
        def __init__(self, context=None): pass


class QuotePlugin(Plugin):
    """
    Inspirational quotes plugin.
    """
    
    QUOTES = [
        {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
        {"quote": "Innovation distinguishes between a leader and a follower.", "author": "Steve Jobs"},
        {"quote": "Stay hungry, stay foolish.", "author": "Steve Jobs"},
        {"quote": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt"},
        {"quote": "It is during our darkest moments that we must focus to see the light.", "author": "Aristotle"},
        {"quote": "The best time to plant a tree was 20 years ago. The second best time is now.", "author": "Chinese Proverb"},
        {"quote": "Your time is limited, don't waste it living someone else's life.", "author": "Steve Jobs"},
        {"quote": "The only impossible journey is the one you never begin.", "author": "Tony Robbins"},
        {"quote": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "author": "Winston Churchill"},
        {"quote": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt"},
        {"quote": "The mind is everything. What you think you become.", "author": "Buddha"},
        {"quote": "Strive not to be a success, but rather to be of value.", "author": "Albert Einstein"},
        {"quote": "The best revenge is massive success.", "author": "Frank Sinatra"},
        {"quote": "I have not failed. I've just found 10,000 ways that won't work.", "author": "Thomas Edison"},
        {"quote": "A person who never made a mistake never tried anything new.", "author": "Albert Einstein"},
    ]
    
    CATEGORIES = {
        "motivation": [0, 3, 4, 7, 9],
        "success": [1, 8, 12, 13],
        "wisdom": [2, 5, 6, 10, 11, 14],
    }
    
    def get_name(self) -> str:
        return "Daily Quote"
    
    def get_description(self) -> str:
        return "Get inspirational quotes"
    
    def get_tools(self) -> List[Dict]:
        return [
            {
                "name": "get_quote",
                "description": "Get a random inspirational quote",
                "handler": self.get_quote,
                "parameters": {
                    "category": "Optional: motivation, success, wisdom",
                },
            },
            {
                "name": "quote_of_the_day",
                "description": "Get today's quote based on the date",
                "handler": self.quote_of_the_day,
                "parameters": {},
            },
        ]
    
    def get_quote(self, category: str = None) -> Dict:
        """
        Get a random quote.
        
        Args:
            category: Optional category filter
            
        Returns:
            Quote dict
        """
        if category and category.lower() in self.CATEGORIES:
            indices = self.CATEGORIES[category.lower()]
            quote = self.QUOTES[random.choice(indices)]
        else:
            quote = random.choice(self.QUOTES)
        
        return {
            "quote": quote["quote"],
            "author": quote["author"],
        }
    
    def quote_of_the_day(self) -> Dict:
        """Get quote based on current day."""
        from datetime import datetime
        
        day_of_year = datetime.now().timetuple().tm_yday
        index = day_of_year % len(self.QUOTES)
        quote = self.QUOTES[index]
        
        return {
            "quote": quote["quote"],
            "author": quote["author"],
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
    
    def on_load(self):
        print(f"[Quote Plugin] Loaded with {len(self.QUOTES)} quotes")


if __name__ == "__main__":
    print("Testing Quote Plugin...")
    
    plugin = QuotePlugin()
    
    # Random quote
    quote = plugin.get_quote()
    print(f"\nRandom Quote:")
    print(f'  "{quote["quote"]}"')
    print(f"  - {quote['author']}")
    
    # Quote of the day
    qotd = plugin.quote_of_the_day()
    print(f"\nQuote of the Day ({qotd['date']}):")
    print(f'  "{qotd["quote"]}"')
    print(f"  - {qotd['author']}")
    
    print("\nQuote plugin test complete!")
