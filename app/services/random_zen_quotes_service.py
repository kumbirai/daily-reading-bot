import logging
import random

import requests

logger = logging.getLogger(__name__)

# The API endpoint
url = "https://zenquotes.io/api/random"

jft = ['*JUST FOR TODAY* my thoughts will be on my recovery, living and enjoying life without the use of drugs.',
       '*JUST FOR TODAY* I will have faith in someone in NA who believes in me and wants to help me in my recovery.',
       '*JUST FOR TODAY* I will have a program. I will try to follow it to the best of my ability.', '*JUST FOR TODAY*, through NA, I will try to get a better perspective on my life.',
       '*JUST FOR TODAY* I will be unafraid. My thoughts will be on my new associations, people who are not using and who have found a new way of life. So long as I follow that way, I have nothing to fear.']


def generate_random_zen_quote() -> str:
    # A GET request to the API
    response = requests.get(url)

    if response.status_code != 200:
        return random.choice(jft)
    # Print the response
    response_json = response.json()
    logger.info(response_json)
    return f"_*{str(response_json[0].get('q')).strip()}*_\n - _{str(response_json[0].get('a')).strip()}_"
