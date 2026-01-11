"""
Test suite for the Radio Tool using pytest and Selenium.
Tests the radio station search and browsing capabilities through the web UI.
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException


# Configuration
BASE_URL = "http://localhost:3000"  # Frontend URL
WAIT_TIMEOUT = 60  # Seconds to wait for responses (API calls can be slow)


@pytest.fixture(scope="module")
def driver():
    """Set up Chrome WebDriver with options."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode for CI
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    
    yield driver
    
    driver.quit()


@pytest.fixture(scope="function")
def chat_page(driver):
    """Navigate to the chat page and wait for it to load."""
    driver.get(BASE_URL)
    
    # Wait for the chat input to be available
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], textarea"))
    )
    
    return driver


def send_message(driver, message: str):
    """Send a message in the chat interface."""
    # Find the input field
    input_field = driver.find_element(By.CSS_SELECTOR, "input[type='text'], textarea")
    input_field.clear()
    input_field.send_keys(message)
    
    # Find and click the send button or press Enter
    try:
        send_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .send-button")
        send_button.click()
    except:
        input_field.send_keys(Keys.RETURN)


def wait_for_response(driver, timeout: int = WAIT_TIMEOUT):
    """Wait for the AI response to appear."""
    # Wait for loading indicator to disappear or response to appear
    time.sleep(2)  # Initial wait for request to start
    
    try:
        # Wait for the response message to appear
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".message.assistant, .ai-message, .response"))
        )
    except TimeoutException:
        pass
    
    # Additional wait for response to complete
    time.sleep(3)


def get_last_response(driver) -> str:
    """Get the text of the last AI response."""
    messages = driver.find_elements(By.CSS_SELECTOR, ".message.assistant, .ai-message, .response, .message-content")
    if messages:
        return messages[-1].text
    return ""


class TestRadioToolSearch:
    """Tests for radio station search functionality."""
    
    def test_search_radio_stations_by_country(self, chat_page):
        """Test searching for radio stations by country."""
        send_message(chat_page, "Find radio stations in Hungary")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        # Verify response contains radio station information
        assert response, "No response received"
        assert any(word in response.lower() for word in ["radio", "station", "hungary", "hungarian", "állomás"]), \
            f"Response should contain radio station info for Hungary. Got: {response[:200]}"
    
    def test_search_radio_stations_by_genre(self, chat_page):
        """Test searching for radio stations by music genre."""
        send_message(chat_page, "Search for jazz radio stations")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["jazz", "radio", "station", "állomás", "zene"]), \
            f"Response should contain jazz radio station info. Got: {response[:200]}"
    
    def test_search_radio_stations_by_name(self, chat_page):
        """Test searching for radio stations by name."""
        send_message(chat_page, "Find radio stations with 'BBC' in the name")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["bbc", "radio", "station", "állomás"]), \
            f"Response should contain BBC radio station info. Got: {response[:200]}"
    
    def test_search_radio_stations_by_language(self, chat_page):
        """Test searching for radio stations by language."""
        send_message(chat_page, "Find radio stations in German language")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["german", "radio", "station", "deutsch", "német", "állomás"]), \
            f"Response should contain German language radio info. Got: {response[:200]}"


class TestRadioToolTopStations:
    """Tests for top/popular radio stations functionality."""
    
    def test_top_radio_stations_by_votes(self, chat_page):
        """Test getting top radio stations by votes."""
        send_message(chat_page, "What are the most popular radio stations?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["popular", "top", "radio", "station", "votes", "népszerű", "állomás"]), \
            f"Response should contain popular radio station info. Got: {response[:200]}"
    
    def test_top_radio_stations_by_clicks(self, chat_page):
        """Test getting top radio stations by clicks."""
        send_message(chat_page, "Which radio stations have the most clicks?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["click", "radio", "station", "popular", "kattintás", "népszerű", "állomás"]), \
            f"Response should contain radio station click info. Got: {response[:200]}"


class TestRadioToolBrowse:
    """Tests for browsing radio station metadata."""
    
    def test_browse_countries(self, chat_page):
        """Test browsing available countries."""
        send_message(chat_page, "Which countries have the most radio stations?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["country", "countries", "radio", "station", "ország", "állomás"]), \
            f"Response should contain country information. Got: {response[:200]}"
    
    def test_browse_languages(self, chat_page):
        """Test browsing available languages."""
        send_message(chat_page, "What languages are available for radio stations?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["language", "radio", "station", "nyelv", "állomás"]), \
            f"Response should contain language information. Got: {response[:200]}"
    
    def test_browse_tags_genres(self, chat_page):
        """Test browsing available tags/genres."""
        send_message(chat_page, "What radio genres are available?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["genre", "tag", "music", "radio", "műfaj", "zene", "állomás"]), \
            f"Response should contain genre/tag information. Got: {response[:200]}"


class TestRadioToolCombinedQueries:
    """Tests for combined/complex radio queries."""
    
    def test_combined_genre_and_country(self, chat_page):
        """Test searching with both genre and country filters."""
        send_message(chat_page, "Find rock stations from the USA")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["rock", "usa", "united states", "radio", "station", "amerikai", "állomás"]), \
            f"Response should contain rock stations from USA. Got: {response[:200]}"
    
    def test_combined_with_limit(self, chat_page):
        """Test searching with a specific limit."""
        send_message(chat_page, "Find 5 jazz stations from France")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["jazz", "france", "french", "radio", "francia", "állomás"]), \
            f"Response should contain jazz stations from France. Got: {response[:200]}"


class TestRadioToolErrorHandling:
    """Tests for error handling in radio tool."""
    
    def test_no_results_query(self, chat_page):
        """Test handling of queries with no results."""
        send_message(chat_page, "Find radio stations in XYZNonExistentCountry123")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        # Should get a response even if no stations found
        assert response, "No response received"
    
    def test_ambiguous_query(self, chat_page):
        """Test handling of ambiguous queries."""
        send_message(chat_page, "radio")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        # Should get some response
        assert response, "No response received"


# Run tests with: pytest test_radio.py -v --html=test_radio_report.html
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--html=test_radio_report.html"])
