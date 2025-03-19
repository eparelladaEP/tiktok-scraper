import streamlit as st
import pandas as pd
import random
import asyncio
import sys
from playwright.async_api import async_playwright
from datetime import datetime

# 📌 Convert TikTok values (e.g., '10K', '2.3M') to numbers
def convert_to_number(value):
    if isinstance(value, str):
        value = value.replace(",", "")  
        if "K" in value:
            return float(value.replace("K", "")) * 1_000
        elif "M" in value:
            return float(value.replace("M", "")) * 1_000_000
        elif value.isdigit():
            return int(value)
    return 0  

# 📌 Function to convert TikTok video ID to date
def tiktok_id_to_date(video_id):
    binary_id = bin(int(video_id))[2:].zfill(64)  # Convert ID to binary
    timestamp_binary = binary_id[:32]  # Extract first 32 bits (timestamp)
    timestamp = int(timestamp_binary, 2)  # Convert binary to int
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')  # Convert to readable date

# 📌 Extract videos matching the date range
async def get_tiktok_data_by_hashtag(hashtag, num_videos, date_range):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        # Open TikTok hashtag page
        url = f"https://www.tiktok.com/tag/{hashtag}"
        await page.goto(url, timeout=120000)

        # Extract start and end dates from selection
        start_date, end_date = date_range
        start_date = start_date.strftime('%Y-%m-%d')
        end_date = end_date.strftime('%Y-%m-%d')

        # Initialize lists
        video_data = []
        total_engagements = 0
        video_links_seen = set()  # Track collected video URLs to prevent duplicates

        # Keep fetching videos until we reach the required number within the date range
        while len(video_data) < num_videos:
            await asyncio.sleep(6)  # Wait for page to load

            # Scroll down to load more videos
            await page.mouse.wheel(0, 5000)
            await asyncio.sleep(7)

            video_elements = await page.query_selector_all("div.css-8dx572-DivContainer-StyledDivContainerV2")

            if not video_elements:  # Stop if no more videos are found
                break  

            for video in video_elements:
                if len(video_data) >= num_videos:
                    break  # Stop once we reach the required number of unique videos

                link_element = await video.query_selector("a")
                link = await link_element.get_attribute("href") if link_element else "N/A"

                if link == "N/A" or link in video_links_seen:
                    continue  # Skip if no link found or duplicate video

                video_links_seen.add(link)  # Mark video as processed

                # Extract video ID and convert it to date
                video_id = link.split("/")[-1]
                video_date = tiktok_id_to_date(video_id)

                # Check if the video date is within the selected range
                if not (start_date <= video_date <= end_date):
                    continue  # Skip videos outside the date range

                # Open the video in a new tab
                video_page = await context.new_page()
                await video_page.goto(link, timeout=30000)
                await asyncio.sleep(random.uniform(5, 8))

                # Extract engagement metrics
                async def safe_extract(selector):
                    try:
                        element = await video_page.query_selector(selector)
                        return convert_to_number(await element.inner_text()) if element else 0
                    except:
                        return 0

                likes = await safe_extract("strong[data-e2e='like-count']")
                comments = await safe_extract("strong[data-e2e='comment-count']")
                shares = await safe_extract("strong[data-e2e='share-count']")
                saves = await safe_extract("strong[data-e2e='undefined-count']")

                # Calculate total engagements
                engagements = likes + comments + shares + saves
                total_engagements += engagements

                video_data.append({
                    "Date": video_date,
                    "Link": link,
                    "Likes": likes,
                    "Comments": comments,
                    "Shares": shares,
                    "Saves": saves,
                    "Total Engagements": engagements
                })

                # Close the video tab
                await video_page.close()

        await browser.close()
        return video_data, total_engagements

# 📌 Streamlit App UI
st.title("📌 TikTok Hashtag Analysis")

# User Input
hashtag = st.text_input("Enter a TikTok hashtag (without #):")
num_videos = st.slider("Number of videos to analyze:", 1, 250, 50)

# Date Selection
date_range = st.date_input("Select a date range to filter videos:", [datetime.today(), datetime.today()])

if st.button("Extract Data") and hashtag:
    with st.spinner("Fetching data..."):
        if sys.platform == "win32":
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
            profile, total_engagements = loop.run_until_complete(get_tiktok_data_by_hashtag(hashtag, num_videos, date_range))
        else:
            profile, total_engagements = asyncio.run(get_tiktok_data_by_hashtag(hashtag, num_videos, date_range))

        df = pd.DataFrame(profile)

        # Display Results
        st.subheader("📊 Filtered Video Data")
        st.dataframe(df)

        # Total Engagements
        total_views = total_engagements / 0.1
        st.subheader("🔥 Total Engagements")
        st.write(f"**Total engagements across {num_videos} videos:** {int(total_engagements)}")
        st.write(f"**Total views across {num_videos} videos:** {int(total_views)}")

        # Download CSV
        csv = df.to_csv(index=False).encode()
        st.download_button("📥 Download Data", csv, f"tiktok_{hashtag}_data.csv", "text/csv")

