import nltk

def download_nltk_data():
    """Download required NLTK data"""
    print("Downloading NLTK data...")
    try:
        # Download required NLTK data
        nltk.download('punkt')
        nltk.download('punkt_tab')
        nltk.download('averaged_perceptron_tagger')
        nltk.download('wordnet')
        print("NLTK data downloaded successfully")
    except Exception as e:
        print(f"Error downloading NLTK data: {e}")
        raise

if __name__ == "__main__":
    download_nltk_data() 