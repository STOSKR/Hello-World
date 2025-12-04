"""
Constants for scraping operations.
Centralized magic numbers and configuration values.
"""

# Extraction limits
STEAM_MAX_LISTINGS = 5  # Maximum Steam listings to extract for average price
BUFF_MAX_SELLING_ITEMS = 25  # Maximum BUFF selling items to extract
BUFF_MAX_TRADE_RECORDS = 25  # Maximum BUFF trade history records

# Price validation
PRICE_DROP_THRESHOLD_PERCENT = (
    10.0  # Max acceptable price drop between trade history and current listings
)

# Volume requirements (default, can be overridden by Settings)
DEFAULT_MIN_VOLUME = 40  # Default minimum volume for liquidity

# Delays (ms) - Anti-ban configuration
BUFF_INITIAL_DELAY_MIN = 500  # Min delay before navigating to BUFF
BUFF_INITIAL_DELAY_MAX = 1500  # Max delay before navigating to BUFF
BUFF_RETRY_DELAY_MIN = 8000  # Min delay before retry on error
BUFF_RETRY_DELAY_MAX = 15000  # Max delay before retry on error

# Timeouts (ms)
BUFF_NAVIGATION_TIMEOUT = 15000  # BUFF page navigation timeout
STEAM_NAVIGATION_TIMEOUT = 10000  # Steam page navigation timeout
BUFF_RETRY_TIMEOUT = 30000  # BUFF retry navigation timeout
PAGE_WAIT_DYNAMIC_CONTENT = 2000  # Wait for dynamic content to load
BLANK_PAGE_RESET_WAIT = 2000  # Wait after navigating to about:blank

# Batch processing
STORAGE_BATCH_SIZE = 10  # Number of items to batch before DB insert

# Filter configuration delays (ms) - Optimized for speed
FILTER_MODAL_CLOSE_WAIT = 500  # Wait after closing modal
FILTER_CURRENCY_INITIAL_WAIT = 500  # Wait before opening currency dropdown
FILTER_DROPDOWN_OPEN_WAIT = 300  # Wait after opening dropdown
FILTER_CURRENCY_RELOAD_WAIT = 1000  # Wait for prices to reload after currency change
FILTER_TAB_SWITCH_WAIT = 300  # Wait after switching tabs
FILTER_INPUT_READY_WAIT = 300  # Wait for filter inputs to be ready
FILTER_PLATFORM_OPEN_WAIT = 500  # Wait after opening platform settings
FILTER_SEARCH_EXECUTE_WAIT = 2000  # Wait after executing search

# Item extraction
ITEM_TABLE_LOAD_TIMEOUT = 10000  # Max time to wait for table to appear
ITEM_TABLE_FALLBACK_WAIT = 2000  # Fallback wait if selector times out
