"""
Test suite for the Book Tool using pytest and Selenium.
Tests the book RAG (Retrieval-Augmented Generation) capabilities for querying
Ferenc Molnár's "Pál Utcai Fiúk" (The Paul Street Boys) through the web UI.
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


class TestBookToolCharacterQueries:
    """Tests for character-related queries about the book."""
    
    def test_query_about_nemecsek(self, chat_page):
        """Test querying about the main character Nemecsek."""
        send_message(chat_page, "Who is Nemecsek in the book?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        # Verify response contains information about Nemecsek
        assert response, "No response received"
        assert any(word in response.lower() for word in ["nemecsek", "boy", "character", "paul street", "pál", "fiú", "karakter"]), \
            f"Response should contain information about Nemecsek. Got: {response[:200]}"
    
    def test_query_about_boka(self, chat_page):
        """Test querying about the character Boka."""
        send_message(chat_page, "Who is Boka in the Paul Street Boys?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["boka", "leader", "boy", "paul street", "pál", "vezér", "elnök", "fiú"]), \
            f"Response should contain information about Boka. Got: {response[:200]}"
    
    def test_query_about_main_characters(self, chat_page):
        """Test querying about the main characters in the book."""
        send_message(chat_page, "Who are the main characters in Pál Utcai Fiúk?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["nemecsek", "boka", "character", "boy", "fiúk", "szereplő", "karakter"]), \
            f"Response should contain information about main characters. Got: {response[:200]}"


class TestBookToolPlotQueries:
    """Tests for plot-related queries about the book."""
    
    def test_query_about_grund(self, chat_page):
        """Test querying about the 'grund' (the vacant lot)."""
        send_message(chat_page, "What is the 'grund' and why is it important to the boys?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["grund", "lot", "place", "boys", "important", "telek", "hely", "fontos", "fiúk"]), \
            f"Response should contain information about the grund. Got: {response[:200]}"
    
    def test_query_about_conflict(self, chat_page):
        """Test querying about the conflict in the story."""
        send_message(chat_page, "What conflict do the Paul Street Boys have with the Redshirts?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["conflict", "redshirt", "fight", "battle", "rival", "gang", "vörösinges", "harc", "csata", "konfliktus"]), \
            f"Response should contain information about the conflict. Got: {response[:200]}"
    
    def test_query_about_ending(self, chat_page):
        """Test querying about the ending of the story."""
        send_message(chat_page, "How does the story of Pál Utcai Fiúk end?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["end", "ending", "final", "conclusion", "nemecsek", "die", "death", "vég", "halál", "meghal"]), \
            f"Response should contain information about the ending. Got: {response[:200]}"


class TestBookToolThemeQueries:
    """Tests for theme-related queries about the book."""
    
    def test_query_about_themes(self, chat_page):
        """Test querying about the main themes of the book."""
        send_message(chat_page, "What are the main themes explored in The Paul Street Boys?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["theme", "friendship", "loyalty", "honor", "childhood", "courage", "barátság", "hűség", "becsület", "gyermekkor", "bátorság", "téma"]), \
            f"Response should contain information about themes. Got: {response[:200]}"
    
    def test_query_about_friendship(self, chat_page):
        """Test querying about friendship in the book."""
        send_message(chat_page, "Describe the relationship between Nemecsek and Boka.")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["nemecsek", "boka", "friend", "relationship", "loyal", "barát", "kapcsolat", "hűség"]), \
            f"Response should contain information about their relationship. Got: {response[:200]}"


class TestBookToolHungarianQueries:
    """Tests for Hungarian language queries (multilingual support)."""
    
    def test_hungarian_query_about_nemecsek(self, chat_page):
        """Test querying in Hungarian about Nemecsek."""
        send_message(chat_page, "Ki Nemecsek a könyvben?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        # Response should be in Hungarian or contain relevant info
        assert any(word in response.lower() for word in ["nemecsek", "fiú", "karakter", "pál utcai", "könyv", "boy", "character"]), \
            f"Response should contain information about Nemecsek. Got: {response[:200]}"
    
    def test_hungarian_query_about_plot(self, chat_page):
        """Test querying in Hungarian about the plot."""
        send_message(chat_page, "Mi a grund és miért fontos a fiúknak?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["grund", "fiúk", "fontos", "hely", "játék", "lot", "important", "boys"]), \
            f"Response should contain information about the grund. Got: {response[:200]}"


class TestBookToolBookInfo:
    """Tests for book information queries."""
    
    def test_query_book_info(self, chat_page):
        """Test querying for general book information."""
        send_message(chat_page, "Tell me about the book Pál Utcai Fiúk")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["molnár", "ferenc", "paul street", "pál utcai", "hungarian", "novel", "regény", "magyar"]), \
            f"Response should contain book information. Got: {response[:200]}"
    
    def test_query_author(self, chat_page):
        """Test querying about the author."""
        send_message(chat_page, "Who wrote The Paul Street Boys?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["molnár", "ferenc", "author", "writer", "hungarian", "író", "szerző", "magyar"]), \
            f"Response should contain author information. Got: {response[:200]}"


class TestBookToolEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_vague_book_query(self, chat_page):
        """Test handling of vague queries about the book."""
        send_message(chat_page, "Tell me something about the book")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        # Should get some response about the book
        assert response, "No response received"
    
    def test_specific_detail_query(self, chat_page):
        """Test querying for specific details."""
        send_message(chat_page, "What role does Nemecsek play in the story?")
        wait_for_response(chat_page)
        
        response = get_last_response(chat_page)
        
        assert response, "No response received"
        assert any(word in response.lower() for word in ["nemecsek", "role", "character", "boy", "brave", "loyal", "szerep", "karakter", "fiú", "bátor", "hűséges"]), \
            f"Response should contain Nemecsek's role. Got: {response[:200]}"


# Run tests with: pytest test_book.py -v --html=test_book_report.html
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--html=test_book_report.html"])
