from flask import Flask, request, render_template
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import re
import time

app = Flask(__name__)

def extract_jsonld_dynamic(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    schemas = []
    error = None

    try:
        driver.get(url)

        # Wait until at least one schema is detected
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//script[@type='application/ld+json']"))
        )

        time.sleep(3)  # Let JS run fully

        # Extract raw text from <script type="application/ld+json">
        script_contents = driver.execute_script("""
            return Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
                         .map(el => el.textContent);
        """)

        for raw_json in script_contents:
            cleaned = re.sub(r'/\*\s*<!\[CDATA\[|\]\]>\s*\*/|//<!\[CDATA\[|//\]\]>', '', raw_json).strip()
            try:
                data = json.loads(cleaned)
                if isinstance(data, list):
                    for item in data:
                        schemas.append({
                            "type": item.get("@type", "Unknown"),
                            "json": json.dumps(item, indent=2)
                        })
                else:
                    schemas.append({
                        "type": data.get("@type", "Unknown"),
                        "json": json.dumps(data, indent=2)
                    })
            except Exception as e:
                # Still show unparsed JSON
                schemas.append({
                    "type": "Invalid JSON",
                    "json": cleaned
                })

    except Exception as e:
        error = str(e)
    finally:
        driver.quit()

    return schemas, error

@app.route('/', methods=['GET', 'POST'])
def index():
    schemas = []
    error = None
    if request.method == 'POST':
        url = request.form.get('url')
        schemas, error = extract_jsonld_dynamic(url)
    return render_template('index.html', schemas=schemas, error=error)

if __name__ == '__main__':
    app.run(debug=True)
