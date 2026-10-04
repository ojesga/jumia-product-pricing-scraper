import time
import logging
import pandas as pd
import matplotlib.pyplot as plt

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Set up simple logging to track progress cleanly
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def setup_driver():
    """Configures and returns a Chrome web driver instance."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    # Real browser user agent to avoid bot detection
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def parse_price(price_str):
    """Utility function to clean raw price strings into float numbers."""
    try:
        cleaned = price_str.replace("₦", "").replace(",", "").strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def fetch_jumia_deals(search_term="laptops"):
    driver = setup_driver()
    items_data = []
    target_url = f"https://www.jumia.com.ng/catalog/?q={search_term}"

    try:
        logging.info(f"Opening Jumia catalog for: '{search_term}'")
        driver.get(target_url)

        # Wait until product cards load
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "prd")))

        # Scroll down slightly to trigger image and element loading
        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(1.5)

        cards = driver.find_elements(By.CLASS_NAME, "prd")
        logging.info(f"Found {len(cards)} item cards on the page.")

        for card in cards:
            try:
                # Name
                name_elem = card.find_element(By.CLASS_NAME, "name")
                name = name_elem.text.strip()

                # Current Price
                price_elem = card.find_element(By.CLASS_NAME, "prc")
                price = parse_price(price_elem.text)

                if not name or not price:
                    continue

                # Old Price (if on discount)
                try:
                    old_price_elem = card.find_element(By.CLASS_NAME, "old")
                    old_price = parse_price(old_price_elem.text)
                except Exception:
                    old_price = price

                # Calculate discount %
                discount = 0.0
                if old_price and old_price > price:
                    discount = round(((old_price - price) / old_price) * 100, 1)

                items_data.append({
                    "Title": name,
                    "Price_NGN": price,
                    "Original_Price_NGN": old_price,
                    "Discount_Pct": discount
                })

            except Exception:
                # Skip any bad rows or promo banners
                continue

    finally:
        driver.quit()

    return items_data


def analyze_and_plot(data, search_term):
    if not data:
        logging.warning("No product data collected to analyze.")
        return

    # Load into Pandas DataFrame
    df = pd.DataFrame(data)
    
    # Sort by cheapest first
    df = df.sort_values(by="Price_NGN", ascending=True).reset_index(drop=True)

    # Print summary to terminal
    print("\n" + "=" * 75)
    print(f" SCRAPED PRODUCT SUMMARY: {search_term.upper()}")
    print("=" * 75)
    for idx, row in df.head(10).iterrows():
        print(f"{idx+1:2d}. {row['Title'][:40]:<40} | ₦{row['Price_NGN']:,.2f} | -{row['Discount_Pct']}%")
    print("=" * 75)

    # Save to CSV
    csv_filename = f"jumia_{search_term}_results.csv"
    df.to_csv(csv_filename, index=False)
    logging.info(f"Saved dataset to '{csv_filename}'")

    # Generate visual plot
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, ax = plt.subplots(figsize=(10, 6))

    top_10 = df.head(10).copy()
    top_10['Short_Title'] = top_10['Title'].apply(lambda x: x[:28] + "..." if len(x) > 28 else x)

    ax.barh(top_10['Short_Title'], top_10['Price_NGN'], color='#2E86AB', edgecolor='black', alpha=0.85)
    ax.set_xlabel("Price in NGN (₦)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Product Name", fontsize=11, fontweight='bold')
    ax.set_title(f"Top 10 Lowest Price Items for '{search_term.title()}' on Jumia", fontsize=13, fontweight='bold')
    ax.invert_yaxis()  # Lowest price on top

    plt.tight_layout()
    chart_filename = f"jumia_{search_term}_prices.png"
    plt.savefig(chart_filename, dpi=300)
    logging.info(f"Saved plot chart to '{chart_filename}'")


# --- TOP-LEVEL EXECUTION ---
keyword = "laptops"
results = fetch_jumia_deals(search_term=keyword)
analyze_and_plot(results, search_term=keyword)