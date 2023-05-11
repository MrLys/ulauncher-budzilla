from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from simplecache import SimpleCache
from fuzzywuzzy import fuzz, process
import logging
import requests
import requests_cache

logger = logging.getLogger(__name__)

# Set up a cache that expires after 1 hour (3600 seconds)
requests_cache.install_cache('my_cache', expire_after=(3600))
cache = SimpleCache('cache.pkl', duration=2*3600)

def fuzzy_search(query, data, threshold=60):
    results = []

    for item in data:
        # We combine the values of each JSON object into a single string,
        # so that we can run the fuzzy matching
        combined_string = f"{item['title']} {item['body']} {item['category']} {item['parent']}"

        # Calculating the fuzzy matching score
        score = fuzz.token_set_ratio(query, combined_string)

        # If the score exceeds the threshold, we add the JSON object to the results
        if score > threshold:
            results.append((item, score))

    # Sorting the results by the score in descending order
    results.sort(key=lambda x: x[1], reverse=True)

    return results


def get_headers(bearer_token):
    return {
        "Authorization": f"Bearer {bearer_token}"
    }

def authorize(url, password):
    loaded_data = cache.load()
    if loaded_data:
        return {"response": loaded_data['jwt'], "status": 200}

    response = requests.post(url,
                             headers={"Content-Type": "application/json"},
                             json={"username":"ljos","password": password})
    loaded_data = {}
    if response.status_code == 200:
        loaded_data['jwt'] = response.json()['jwt']
        cache.save(loaded_data)
        return {"response": response.json()['jwt'], "status": 200}
    elif response.status_code == 404:
        cache.clear()
        return {"response": "Incorrect username or password", "status": response.status_code}
    else:
        return {"response": "Error during authorization", "status": response.status_code}

class BudzillaExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):
        items = []
        response = authorize(extension.preferences['budzilla_auth_url'], extension.preferences['budzilla_password'])
        argument = event.get_argument();
        if response['status'] != 200:
            items.append(ExtensionResultItem(icon='images/budzilla1_cropped.png',
                                             name='Error',
                                             description=response['response'],
                                             on_enter=HideWindowAction()))
            return RenderResultListAction(items)
        bearer_token = response['response']

        response = requests.get(extension.preferences['budzilla_entry_url'], headers=get_headers(bearer_token))
        data = response.json()
        logger.debug(data)
        if response.status_code == 404:
            # evict cache
            cache.clear()
            items.append(ExtensionResultItem(icon='images/budzilla1_cropped.png',
                                             name='Unauthorized',
                                             description="error %s" % response.status_code,
                                             on_enter=HideWindowAction()))
        if response.status_code != 200:
            cache.clear()
            items.append(ExtensionResultItem(icon='images/budzilla1_cropped.png',
                                             name='Error',
                                             description="error %s" % response.status_code,
                                             on_enter=HideWindowAction()))
            return RenderResultListAction(items)


        # Process the response data as needed
        sorted_data = fuzzy_search(argument, data)

        for entry in sorted_data:
            items.append(ExtensionResultItem(icon='images/budzilla1_cropped.png',
                                             name='%s' % entry[0]['title'],
                                             description='%s' % entry[0]['body'],
                                             on_enter=CopyToClipboardAction(entry[0]['body'])))

        return RenderResultListAction(items)

if __name__ == '__main__':
    BudzillaExtension().run()


